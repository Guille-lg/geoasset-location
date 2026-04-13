import logging
import math
import re
from typing import List

from app.pipeline.models import DocumentExtractedAsset

logger = logging.getLogger(__name__)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _close_coordinates(a: DocumentExtractedAsset, b: DocumentExtractedAsset) -> bool:
    if a.latitude is None or a.longitude is None or b.latitude is None or b.longitude is None:
        return False
    return math.dist((a.latitude, a.longitude), (b.latitude, b.longitude)) <= 0.02


def _same_asset(a: DocumentExtractedAsset, b: DocumentExtractedAsset) -> bool:
    if _normalize(a.asset_name) == _normalize(b.asset_name):
        return True
    if a.address and b.address and _normalize(a.address) == _normalize(b.address):
        return True
    return _close_coordinates(a, b)


def deduplicate_document_assets(items: List[DocumentExtractedAsset]) -> List[DocumentExtractedAsset]:
    merged: List[DocumentExtractedAsset] = []

    for item in items:
        target = next((current for current in merged if _same_asset(current, item)), None)
        if not target:
            merged.append(item)
            continue

        if len(item.asset_name) > len(target.asset_name):
            target.asset_name = item.asset_name

        if item.address and (not target.address or len(item.address) > len(target.address)):
            target.address = item.address

        target.location_hints = sorted(set(target.location_hints + item.location_hints))

        if item.evidence_quote:
            if target.evidence_quote:
                target.evidence_quote = f"{target.evidence_quote}\n---\n{item.evidence_quote}"
            else:
                target.evidence_quote = item.evidence_quote

        if item.latitude is not None and item.longitude is not None:
            target.latitude = item.latitude
            target.longitude = item.longitude

        target.llm_confidence = max(target.llm_confidence, item.llm_confidence)

    logger.info("Doc Step D3: deduplicated %s mentions to %s assets", len(items), len(merged))
    return merged
