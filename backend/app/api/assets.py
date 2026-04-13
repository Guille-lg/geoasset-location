import logging
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.pipeline.models import AnalyzeRequest
from app.pipeline.orchestrator import run_pipeline_sse
from app.services.cache import get_cached_assets

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])


@router.post("/analyze")
async def analyze_assets(request: AnalyzeRequest):
    if not request.force_refresh:
        cached = await get_cached_assets(request.company_id)
        if cached:
            return {
                "cached": True,
                "assets": cached.get("assets", []),
                "metadata": cached.get("metadata", {}),
            }

    return StreamingResponse(
        run_pipeline_sse(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{company_id}")
async def get_assets(
    company_id: str,
    category: Optional[str] = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
):
    cached = await get_cached_assets(company_id)
    if not cached:
        return {"assets": [], "metadata": {"total_assets": 0}}

    assets = cached.get("assets", [])

    if category:
        assets = [a for a in assets if a.get("category") == category]
    if min_confidence > 0:
        assets = [a for a in assets if a.get("confidence_score", 0) >= min_confidence]

    return {"assets": assets, "metadata": cached.get("metadata", {})}
