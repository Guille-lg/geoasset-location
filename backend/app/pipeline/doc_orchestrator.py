import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator

from app.pipeline.models import Asset, CompanyInfo, DocumentScoredAsset
from app.pipeline.orchestrator import _persist_assets
from app.pipeline.steps.doc_step0_parse import parse_uploaded_document
from app.pipeline.steps.doc_step1_chunk import chunk_document
from app.pipeline.steps.doc_step2_extract import extract_assets_from_chunks
from app.pipeline.steps.doc_step3_dedup import deduplicate_document_assets
from app.pipeline.steps.doc_step4_geocode import geocode_and_enrich_document_assets
from app.pipeline.steps.doc_step5_scoring import score_document_assets
from app.services.cache import get_cached_assets, set_cached_assets

logger = logging.getLogger(__name__)


def _doc_scored_to_asset(s: DocumentScoredAsset, company_id: str) -> Asset:
    return Asset(
        id=str(uuid.uuid4()),
        company_id=company_id,
        name=s.name,
        raw_name=s.raw_name,
        category=s.category,
        latitude=s.latitude,
        longitude=s.longitude,
        address=s.address,
        municipality=s.municipality,
        province=s.province,
        autonomous_community=s.autonomous_community,
        postal_code=s.postal_code,
        description=s.description,
        size_estimate=s.size_estimate,
        functional_tags=s.functional_tags,
        is_headquarters=s.is_headquarters,
        google_place_id=s.place_id,
        confidence_score=s.confidence_score,
        confidence_tier=s.confidence_tier,
        data_sources=s.data_sources,
        website=s.website,
        phone=s.phone,
    )


async def run_doc_pipeline_sse(
    *,
    company_id: str,
    company_name: str,
    file_name: str,
    file_bytes: bytes,
    force_refresh: bool,
) -> AsyncGenerator[str, None]:
    job_id = str(uuid.uuid4())

    def sse_event(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

    yield sse_event("job_started", {"job_id": job_id, "company_name": company_name, "file_name": file_name})

    if not force_refresh:
        cached = await get_cached_assets(company_id)
        if cached:
            yield sse_event(
                "complete",
                {
                    "cached": True,
                    "assets": cached.get("assets", []),
                    "metadata": cached.get("metadata", {}),
                },
            )
            return

    company_info = CompanyInfo(id=company_id, name=company_name)

    try:
        yield sse_event("step_start", {"step": 0, "name": "Parsing uploaded document", "estimated_seconds": 8})
        markdown = await parse_uploaded_document(file_name, file_bytes)
        yield sse_event("step_complete", {"step": 0, "name": "Document parsed", "found": len(markdown)})

        yield sse_event("step_start", {"step": 1, "name": "Chunking structured content", "estimated_seconds": 3})
        chunks = await chunk_document(markdown)
        yield sse_event("step_complete", {"step": 1, "name": "Chunking complete", "found": len(chunks)})

        if not chunks:
            yield sse_event(
                "complete",
                {"assets": [], "metadata": {"total_assets": 0, "company": company_info.model_dump()}},
            )
            return

        yield sse_event("step_start", {"step": 2, "name": "Extracting assets with AI", "estimated_seconds": 20})
        extracted = await extract_assets_from_chunks(chunks, company_name)
        yield sse_event("step_complete", {"step": 2, "name": "Extraction complete", "found": len(extracted)})

        if not extracted:
            yield sse_event(
                "complete",
                {"assets": [], "metadata": {"total_assets": 0, "company": company_info.model_dump()}},
            )
            return

        yield sse_event("step_start", {"step": 3, "name": "Deduplicating asset mentions", "estimated_seconds": 2})
        deduplicated = deduplicate_document_assets(extracted)
        yield sse_event("step_complete", {"step": 3, "name": "Deduplication complete", "found": len(deduplicated)})

        yield sse_event("step_start", {"step": 4, "name": "Geocoding and enrichment", "estimated_seconds": 12})
        geocoded = await geocode_and_enrich_document_assets(deduplicated, company_name)
        yield sse_event("step_complete", {"step": 4, "name": "Geocoding complete", "found": len(geocoded)})

        yield sse_event("step_start", {"step": 5, "name": "Scoring confidence", "estimated_seconds": 2})
        scored = await score_document_assets(geocoded)
        yield sse_event("step_complete", {"step": 5, "name": "Scoring complete", "found": len(scored)})

        assets = [_doc_scored_to_asset(asset, company_id) for asset in scored]
        assets_data = [asset.model_dump() for asset in assets]

        high_conf = sum(1 for asset in assets if asset.confidence_tier == "HIGH")
        med_conf = sum(1 for asset in assets if asset.confidence_tier == "MEDIUM")
        low_conf = sum(1 for asset in assets if asset.confidence_tier == "LOW")

        metadata = {
            "company": company_info.model_dump(),
            "total_assets": len(assets),
            "high_confidence": high_conf,
            "medium_confidence": med_conf,
            "low_confidence": low_conf,
            "source": "document_upload",
            "file_name": file_name,
            "last_updated": datetime.utcnow().isoformat(),
        }

        await set_cached_assets(company_id, {"assets": assets_data, "metadata": metadata})
        asyncio.create_task(_persist_assets(assets, company_info))

        yield sse_event("complete", {"assets": assets_data, "metadata": metadata})
    except Exception as exc:
        logger.exception("Document pipeline error: %s", exc)
        yield sse_event("error", {"message": str(exc)})
