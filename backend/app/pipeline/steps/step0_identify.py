import logging
import re

from app.pipeline.models import CompanyInfo

logger = logging.getLogger(__name__)


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().strip())
    return s.strip("_")


async def identify_company(query: str) -> CompanyInfo:
    clean_query = query.strip()
    return CompanyInfo(id=_slug(clean_query), name=clean_query)
