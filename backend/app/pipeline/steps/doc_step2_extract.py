import asyncio
import logging
import os
from typing import List

import yaml

from app.pipeline.models import AssetCategory, DocumentExtractedAsset
from app.core.config import settings
from app.services.llm_client import llm_json

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "v1", "extract_doc_assets.yaml")
_PROMPT_TEMPLATE: dict | None = None


def _load_prompt() -> dict:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        with open(PROMPT_PATH, "r") as f:
            _PROMPT_TEMPLATE = yaml.safe_load(f)
    return _PROMPT_TEMPLATE


async def extract_assets_from_chunks(chunks: List[str], company_name: str) -> List[DocumentExtractedAsset]:
    if not chunks:
        return []

    prompt_template = _load_prompt()

    semaphore = asyncio.Semaphore(max(1, settings.DOC_EXTRACTION_MAX_CONCURRENCY))

    async def process_chunk(chunk_text: str, chunk_index: int) -> List[DocumentExtractedAsset]:
        async with semaphore:
            system_msg = prompt_template["system"]
            user_msg = (
                prompt_template["user"]
                .replace("{company_name}", company_name)
                .replace("{chunk_index}", str(chunk_index))
                .replace("{chunk_text}", chunk_text)
            )

            result = await llm_json(
                [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ]
            )

            if not result or "results" not in result:
                return []

            extracted: List[DocumentExtractedAsset] = []
            for item in result["results"]:
                raw_category = item.get("category", "OTR")
                try:
                    category = AssetCategory(raw_category)
                except ValueError:
                    category = AssetCategory.OTR

                coords_lat = item.get("latitude")
                coords_lon = item.get("longitude")

                extracted.append(
                    DocumentExtractedAsset(
                        asset_name=item.get("asset_name", "").strip() or "Unlabeled asset",
                        category=category,
                        location_hints=item.get("location_hints", []) or [],
                        address=item.get("address"),
                        latitude=float(coords_lat) if isinstance(coords_lat, (int, float)) else None,
                        longitude=float(coords_lon) if isinstance(coords_lon, (int, float)) else None,
                        evidence_quote=item.get("evidence_quote"),
                        llm_confidence=float(item.get("confidence", 0.5)),
                        source_chunk=chunk_index,
                    )
                )
            return extracted

    tasks = [process_chunk(chunk, idx) for idx, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_extracted: List[DocumentExtractedAsset] = []
    for result in results:
        if isinstance(result, list):
            all_extracted.extend(result)
        elif isinstance(result, Exception):
            logger.error("Doc extraction chunk failed: %s", result)

    logger.info(
        "Doc Step D2: extracted %s asset mentions from %s chunks for '%s'",
        len(all_extracted),
        len(chunks),
        company_name,
    )
    return all_extracted
