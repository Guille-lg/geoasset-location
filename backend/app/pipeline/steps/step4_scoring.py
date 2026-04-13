import logging
from typing import List

from scipy.stats import beta as beta_dist

from app.core.config import settings
from app.pipeline.models import EnrichedAsset, ScoredAsset

logger = logging.getLogger(__name__)

SIGNALS_WEIGHTS = {
    "name_match": 0.30,
    "type_match": 0.20,
    "address_corporate": 0.15,
    "website_match": 0.15,
    "reviews_b2b": 0.10,
    "llm_confidence": 0.10,
}

PRODUCTIVE_TYPES = {
    "corporate_office", "office", "warehouse", "storage",
    "factory", "industrial_area", "logistics", "store",
    "supermarket", "shopping_mall", "hospital", "hotel",
    "lodging", "farm", "airport", "train_station",
    "establishment", "point_of_interest",
}


def _name_match_signal(asset: EnrichedAsset, company_name: str) -> float:
    cn = company_name.lower().split()[0]
    return 1.0 if cn in asset.raw_name.lower() or cn in asset.name.lower() else 0.0


def _type_match_signal(asset: EnrichedAsset) -> float:
    if not asset.types:
        return 0.3
    overlap = set(asset.types) & PRODUCTIVE_TYPES
    return min(len(overlap) / 2, 1.0) if overlap else 0.2


def _website_match_signal(asset: EnrichedAsset, company_name: str) -> float:
    if not asset.website:
        return 0.0
    cn = company_name.lower().split()[0].replace(" ", "")
    return 0.9 if cn in asset.website.lower() else 0.1


def _reviews_signal(asset: EnrichedAsset) -> float:
    if not asset.user_ratings_total:
        return 0.3
    if asset.user_ratings_total > 100:
        return 0.8
    if asset.user_ratings_total > 20:
        return 0.5
    return 0.3


def compute_confidence(asset: EnrichedAsset, company_name: str) -> float:
    signals = {
        "name_match": _name_match_signal(asset, company_name),
        "type_match": _type_match_signal(asset),
        "address_corporate": 0.5,
        "website_match": _website_match_signal(asset, company_name),
        "reviews_b2b": _reviews_signal(asset),
        "llm_confidence": asset.llm_confidence,
    }

    raw_score = sum(SIGNALS_WEIGHTS[k] * signals[k] for k in SIGNALS_WEIGHTS)

    alpha = 1 + raw_score * 10
    beta_param = 1 + (1 - raw_score) * 10
    smoothed = beta_dist.mean(alpha, beta_param)

    return round(smoothed, 3)


def get_confidence_tier(score: float) -> str:
    if score >= settings.CONFIDENCE_THRESHOLD_HIGH:
        return "HIGH"
    elif score >= settings.CONFIDENCE_THRESHOLD_MEDIUM:
        return "MEDIUM"
    return "LOW"


async def score_assets(assets: List[EnrichedAsset], company_name: str) -> List[ScoredAsset]:
    scored: List[ScoredAsset] = []
    for asset in assets:
        score = compute_confidence(asset, company_name)
        tier = get_confidence_tier(score)
        scored.append(
            ScoredAsset(
                **asset.model_dump(),
                confidence_score=score,
                confidence_tier=tier,
            )
        )
    scored.sort(key=lambda a: a.confidence_score, reverse=True)
    logger.info(f"Step 4: Scored {len(scored)} assets for '{company_name}'")
    return scored
