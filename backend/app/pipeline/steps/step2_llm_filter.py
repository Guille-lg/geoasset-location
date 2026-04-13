import asyncio
import json
import logging
import os
from typing import List

import yaml

from app.pipeline.models import AssetCategory, FilteredAsset, RawPlace
from app.services.llm_client import llm_json

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "v1", "filter_assets.yaml")


def _load_prompt() -> dict:
    with open(PROMPT_PATH, "r") as f:
        return yaml.safe_load(f)


def _batch(items: list, size: int = 20) -> list:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def filter_and_classify(places: List[RawPlace], company_name: str) -> List[FilteredAsset]:
    if not places:
        return []

    prompt_template = _load_prompt()
    batches = _batch(places, 20)
    all_filtered: List[FilteredAsset] = []

    async def process_batch(batch: List[RawPlace]) -> List[FilteredAsset]:
        places_data = [
            {
                "place_id": p.place_id,
                "name": p.name,
                "address": p.address,
                "types": p.types,
                "website": p.website or "",
                "rating": p.rating,
                "user_ratings_total": p.user_ratings_total,
            }
            for p in batch
        ]

        system_msg = prompt_template["system"].replace("{company_name}", company_name)
        user_msg = prompt_template["user"].replace("{company_name}", company_name).replace(
            "{places_json}", json.dumps(places_data, ensure_ascii=False, indent=2)
        )

        result = await llm_json([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ])

        if not result or "results" not in result:
            return []

        filtered = []
        place_map = {p.place_id: p for p in batch}
        for item in result["results"]:
            if not item.get("is_productive_asset", False):
                continue
            pid = item.get("place_id", "")
            original = place_map.get(pid)
            if not original:
                continue

            try:
                cat = AssetCategory(item.get("category", "OTR"))
            except ValueError:
                cat = AssetCategory.OTR

            filtered.append(
                FilteredAsset(
                    place_id=original.place_id,
                    raw_name=original.name,
                    name=item.get("name", original.name),
                    category=cat,
                    is_headquarters=item.get("is_headquarters", False),
                    address=original.address,
                    latitude=original.latitude,
                    longitude=original.longitude,
                    types=original.types,
                    website=original.website,
                    phone=original.phone,
                    rating=original.rating,
                    user_ratings_total=original.user_ratings_total,
                    llm_confidence=item.get("confidence", 0.5),
                )
            )
        return filtered

    tasks = [process_batch(b) for b in batches]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, list):
            all_filtered.extend(r)
        elif isinstance(r, Exception):
            logger.error(f"Batch filter error: {r}")

    keep_rate = (len(all_filtered) / len(places) * 100) if places else 0.0
    logger.info(
        "LLM filter summary for '%s': candidates_in=%s kept=%s keep_rate=%.2f%%",
        company_name,
        len(places),
        len(all_filtered),
        keep_rate,
    )
    return all_filtered
