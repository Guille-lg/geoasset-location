import asyncio
import logging
import os
import re
import uuid
from typing import List, Optional

import httpx
import yaml

from app.core.config import settings
from app.pipeline.models import DocumentEnrichedAsset, DocumentExtractedAsset
from app.services.llm_client import llm_json

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "v1", "geocode_assets.yaml")
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
_PROMPT_TEMPLATE: dict | None = None


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _load_prompt() -> dict:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        with open(PROMPT_PATH, "r") as f:
            _PROMPT_TEMPLATE = yaml.safe_load(f)
    return _PROMPT_TEMPLATE


async def _geocode_google(query: str, client: httpx.AsyncClient) -> Optional[dict]:
    if not settings.GOOGLE_MAPS_API_KEY:
        return None

    params = {"address": query, "key": settings.GOOGLE_MAPS_API_KEY, "region": "es", "language": "es"}
    try:
        response = await client.get(GEOCODE_URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "OK" or not payload.get("results"):
            return None

        result = payload["results"][0]
        location = result.get("geometry", {}).get("location", {})
        return {
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "address": result.get("formatted_address"),
        }
    except Exception as exc:
        logger.warning("Doc geocode fallback failed for '%s': %s", query, exc)
        return None


async def _geocode_llm(asset: DocumentExtractedAsset, company_name: str, prompt_template: dict) -> Optional[dict]:
    location_hints = ", ".join(asset.location_hints) if asset.location_hints else ""
    user_msg = (
        prompt_template["user"]
        .replace("{company_name}", company_name)
        .replace("{asset_name}", asset.asset_name)
        .replace("{category}", asset.category.value)
        .replace("{address}", asset.address or "")
        .replace("{location_hints}", location_hints)
        .replace("{evidence_quote}", asset.evidence_quote or "")
    )

    result = await llm_json(
        [
            {"role": "system", "content": prompt_template["system"]},
            {"role": "user", "content": user_msg},
        ]
    )
    return result if isinstance(result, dict) else None


async def geocode_and_enrich_document_assets(
    assets: List[DocumentExtractedAsset], company_name: str
) -> List[DocumentEnrichedAsset]:
    if not assets:
        return []

    prompt_template = _load_prompt()

    semaphore = asyncio.Semaphore(max(1, settings.DOC_GEOCODE_MAX_CONCURRENCY))
    geocode_cache: dict[str, Optional[dict]] = {}

    async with httpx.AsyncClient() as geocode_client:
        async def enrich(asset: DocumentExtractedAsset, idx: int) -> DocumentEnrichedAsset:
            async with semaphore:
                latitude = asset.latitude
                longitude = asset.longitude
                address = asset.address or ""
                municipality = ""
                province = ""
                autonomous_community = ""
                postal_code = None
                coordinate_source = "reported" if latitude is not None and longitude is not None else "unknown"

                if latitude is None or longitude is None:
                    query = ""
                    if address or asset.location_hints:
                        query = f"{asset.asset_name}, {address or ', '.join(asset.location_hints)}, España"

                    fallback = None
                    if query:
                        if query not in geocode_cache:
                            geocode_cache[query] = await _geocode_google(query, geocode_client)
                        fallback = geocode_cache[query]

                    if fallback and isinstance(fallback.get("latitude"), (int, float)) and isinstance(fallback.get("longitude"), (int, float)):
                        latitude = float(fallback["latitude"])
                        longitude = float(fallback["longitude"])
                        address = fallback.get("address") or address
                        coordinate_source = "google_geocoding"

                if latitude is None or longitude is None:
                    llm_guess = await _geocode_llm(asset, company_name, prompt_template)
                    if llm_guess:
                        guess_lat = llm_guess.get("latitude")
                        guess_lon = llm_guess.get("longitude")
                        if isinstance(guess_lat, (int, float)) and isinstance(guess_lon, (int, float)):
                            latitude = float(guess_lat)
                            longitude = float(guess_lon)
                            coordinate_source = "llm"
                        if llm_guess.get("address"):
                            address = llm_guess.get("address")
                        municipality = llm_guess.get("municipality", "") or ""
                        province = llm_guess.get("province", "") or ""
                        autonomous_community = llm_guess.get("autonomous_community", "") or ""
                        postal_code = llm_guess.get("postal_code")

                if latitude is None or longitude is None:
                    latitude = 40.4168
                    longitude = -3.7038
                    coordinate_source = "default"

                evidence_count = 0
                if asset.evidence_quote:
                    evidence_count = max(1, asset.evidence_quote.count("\n---\n") + 1)

                return DocumentEnrichedAsset(
                    **asset.model_dump(),
                    place_id=f"doc_{_slug(company_name)}_{idx}_{uuid.uuid4().hex[:8]}",
                    raw_name=asset.asset_name,
                    name=asset.asset_name,
                    latitude=latitude,
                    longitude=longitude,
                    address=address or ", ".join(asset.location_hints) or "Ubicación no especificada",
                    municipality=municipality,
                    province=province,
                    autonomous_community=autonomous_community,
                    postal_code=postal_code,
                    coordinate_source=coordinate_source,
                    evidence_count=evidence_count,
                )

        tasks = [enrich(asset, idx) for idx, asset in enumerate(assets)]
        enriched = await asyncio.gather(*tasks)

    logger.info("Doc Step D4: geocoded/enriched %s assets", len(enriched))
    return enriched
