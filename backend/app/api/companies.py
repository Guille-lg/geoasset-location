import logging
from typing import List

from fastapi import APIRouter, Query

from app.pipeline.steps.step0_identify import identify_company
from app.services.google_maps import search_company_candidates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])


@router.get("/search")
async def search_companies(q: str = Query(..., min_length=3), limit: int = Query(10, ge=1, le=20)):
    candidates = await search_company_candidates(q, limit=limit)

    companies = []
    for c in candidates:
        name = c.get("displayName", {}).get("text", "")
        companies.append({
            "id": name.lower().replace(" ", "_").replace(".", ""),
            "name": name,
            "address": c.get("formattedAddress", ""),
            "types": c.get("types", []),
            "website": c.get("websiteUri", ""),
        })

    return {"companies": companies}
