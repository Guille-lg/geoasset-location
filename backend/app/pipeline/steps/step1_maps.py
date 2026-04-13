import logging
from typing import List

from app.pipeline.models import RawPlace
from app.services.google_maps import search_company_assets

logger = logging.getLogger(__name__)


async def search_maps(company_name: str) -> List[RawPlace]:
    places = await search_company_assets(company_name)
    logger.info(f"Step 1: Found {len(places)} raw places for '{company_name}'")
    return places
