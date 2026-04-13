import asyncio
import json
import logging
import os
from typing import List

import yaml

from app.pipeline.models import EnrichedAsset, FilteredAsset
from app.services.llm_client import llm_json

logger = logging.getLogger(__name__)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "v1", "enrich_asset.yaml")


def _load_prompt() -> dict:
    with open(PROMPT_PATH, "r") as f:
        return yaml.safe_load(f)


def _batch(items: list, size: int = 15) -> list:
    return [items[i : i + size] for i in range(0, len(items), size)]


async def enrich_assets(assets: List[FilteredAsset], company_name: str) -> List[EnrichedAsset]:
    if not assets:
        return []

    prompt_template = _load_prompt()
    batches = _batch(assets, 15)
    all_enriched: List[EnrichedAsset] = []

    async def process_batch(batch: List[FilteredAsset]) -> List[EnrichedAsset]:
        assets_data = [
            {
                "place_id": a.place_id,
                "name": a.name,
                "category": a.category.value,
                "address": a.address,
                "website": a.website or "",
            }
            for a in batch
        ]

        system_msg = prompt_template["system"].replace("{company_name}", company_name)
        user_msg = prompt_template["user"].replace("{company_name}", company_name).replace(
            "{assets_json}", json.dumps(assets_data, ensure_ascii=False, indent=2)
        )

        result = await llm_json([
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ])

        enriched = []
        enrich_map = {}
        if result and "results" in result:
            for item in result["results"]:
                enrich_map[item.get("place_id", "")] = item

        for asset in batch:
            info = enrich_map.get(asset.place_id, {})
            enriched.append(
                EnrichedAsset(
                    **asset.model_dump(),
                    description=info.get("description") or "",
                    size_estimate=info.get("size_estimate") or "MEDIUM",
                    functional_tags=info.get("functional_tags") or [],
                    municipality=info.get("municipality") or "",
                    province=info.get("province") or "",
                    autonomous_community=info.get("autonomous_community") or "",
                    postal_code=info.get("postal_code"),
                )
            )
        return enriched

    tasks = [process_batch(b) for b in batches]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        if isinstance(r, list):
            all_enriched.extend(r)
        elif isinstance(r, Exception):
            logger.error(f"Batch enrich error: {r}")

    logger.info(f"Step 3: Enriched {len(all_enriched)} assets for '{company_name}'")
    return all_enriched
