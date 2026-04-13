import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import AsyncGenerator, Dict, Optional

from app.pipeline.models import Asset, AnalyzeRequest, CompanyInfo, ScoredAsset
from app.pipeline.steps.step0_identify import identify_company
from app.pipeline.steps.step1_maps import search_maps
from app.pipeline.steps.step2_llm_filter import filter_and_classify
from app.pipeline.steps.step3_enrich import enrich_assets
from app.pipeline.steps.step4_scoring import score_assets
from app.services.cache import get_cached_assets, set_cached_assets, invalidate_cache

logger = logging.getLogger(__name__)

_jobs: Dict[str, dict] = {}


def _scored_to_asset(s: ScoredAsset, company_id: str) -> Asset:
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


async def run_pipeline_sse(request: AnalyzeRequest) -> AsyncGenerator[str, None]:
    job_id = str(uuid.uuid4())
    company_name = request.company_name
    company_id = request.company_id

    def sse_event(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

    yield sse_event("job_started", {"job_id": job_id, "company_name": company_name})

    # Check cache
    if not request.force_refresh:
        cached = await get_cached_assets(company_id)
        if cached:
            yield sse_event("complete", {
                "cached": True,
                "assets": cached.get("assets", []),
                "metadata": cached.get("metadata", {}),
            })
            return

    try:
        # Step 0: Identify company
        yield sse_event("step_start", {"step": 0, "name": "Identificando empresa", "estimated_seconds": 3})
        company_info = await identify_company(company_name)
        company_id = company_info.id
        yield sse_event("step_complete", {
            "step": 0,
            "name": "Empresa identificada",
            "company": company_info.model_dump(),
        })

        # Step 1: Search Google Maps
        yield sse_event("step_start", {"step": 1, "name": "Buscando en Google Maps", "estimated_seconds": 15})
        raw_places = await search_maps(company_info.name)
        yield sse_event("step_complete", {
            "step": 1,
            "name": "Búsqueda en Google Maps completada",
            "found": len(raw_places),
        })

        if not raw_places:
            yield sse_event("complete", {
                "assets": [],
                "metadata": {"total_assets": 0, "company": company_info.model_dump()},
            })
            return

        # Step 2: LLM filter and classify
        yield sse_event("step_start", {"step": 2, "name": "Clasificando activos con IA", "estimated_seconds": 25})
        filtered = await filter_and_classify(raw_places, company_info.name)
        yield sse_event("step_complete", {
            "step": 2,
            "name": "Clasificación completada",
            "found": len(filtered),
        })

        if not filtered:
            yield sse_event("complete", {
                "assets": [],
                "metadata": {"total_assets": 0, "company": company_info.model_dump()},
            })
            return

        # Step 3: Enrich
        yield sse_event("step_start", {"step": 3, "name": "Enriqueciendo datos", "estimated_seconds": 15})
        enriched = await enrich_assets(filtered, company_info.name)
        yield sse_event("step_complete", {
            "step": 3,
            "name": "Enriquecimiento completado",
            "found": len(enriched),
        })

        # Step 4: Score
        yield sse_event("step_start", {"step": 4, "name": "Calculando confianza", "estimated_seconds": 3})
        scored = await score_assets(enriched, company_info.name)
        yield sse_event("step_complete", {
            "step": 4,
            "name": "Scoring completado",
            "found": len(scored),
        })

        # Convert to final assets
        assets = [_scored_to_asset(s, company_id) for s in scored]
        assets_data = [a.model_dump() for a in assets]

        high_conf = sum(1 for a in assets if a.confidence_tier == "HIGH")
        med_conf = sum(1 for a in assets if a.confidence_tier == "MEDIUM")
        low_conf = sum(1 for a in assets if a.confidence_tier == "LOW")

        metadata = {
            "company": company_info.model_dump(),
            "total_assets": len(assets),
            "high_confidence": high_conf,
            "medium_confidence": med_conf,
            "low_confidence": low_conf,
            "last_updated": datetime.utcnow().isoformat(),
        }

        # Cache results
        await set_cached_assets(company_id, {"assets": assets_data, "metadata": metadata})

        # Store in DB (fire-and-forget)
        asyncio.create_task(_persist_assets(assets, company_info))

        yield sse_event("complete", {"assets": assets_data, "metadata": metadata})

    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
        yield sse_event("error", {"message": str(e)})


async def _persist_assets(assets: list, company_info: CompanyInfo):
    try:
        from app.db.session import async_session
        from app.db.models import AssetRecord, CompanyRecord
        from sqlalchemy import delete

        async with async_session() as session:
            # Upsert company
            from sqlalchemy.dialects.postgresql import insert
            stmt = insert(CompanyRecord).values(
                id=company_info.id,
                name=company_info.name,
                cif=company_info.cif,
                sector=company_info.sector,
                cnae=company_info.cnae,
                headquarters=company_info.headquarters,
                last_analyzed_at=datetime.utcnow(),
                total_assets=len(assets),
            ).on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": company_info.name,
                    "last_analyzed_at": datetime.utcnow(),
                    "total_assets": len(assets),
                },
            )
            await session.execute(stmt)

            # Delete old assets for this company
            await session.execute(delete(AssetRecord).where(AssetRecord.company_id == company_info.id))

            # Insert new
            for asset in assets:
                record = AssetRecord(
                    id=asset.id,
                    company_id=asset.company_id,
                    name=asset.name,
                    raw_name=asset.raw_name,
                    category=asset.category.value if hasattr(asset.category, "value") else asset.category,
                    latitude=asset.latitude,
                    longitude=asset.longitude,
                    address=asset.address,
                    municipality=asset.municipality,
                    province=asset.province,
                    autonomous_community=asset.autonomous_community,
                    postal_code=asset.postal_code,
                    description=asset.description,
                    size_estimate=asset.size_estimate,
                    functional_tags=asset.functional_tags,
                    is_headquarters=asset.is_headquarters,
                    google_place_id=asset.google_place_id,
                    confidence_score=asset.confidence_score,
                    confidence_tier=asset.confidence_tier,
                    data_sources=asset.data_sources,
                    website=asset.website,
                    phone=asset.phone,
                )
                session.add(record)

            await session.commit()
            logger.info(f"Persisted {len(assets)} assets for company {company_info.id}")
    except Exception as e:
        logger.error(f"Failed to persist assets: {e}")
