import asyncio
import logging
from typing import List, Optional

import httpx

from app.core.config import settings
from app.pipeline.models import CATEGORY_SEARCH_KEYWORDS, RawPlace

logger = logging.getLogger(__name__)

SPAIN_PROVINCES = [
    "A Coruna",
    "Albacete",
    "Alicante",
    "Almeria",
    "Asturias",
    "Avila",
    "Badajoz",
    "Barcelona",
    "Burgos",
    "Caceres",
    "Cadiz",
    "Cantabria",
    "Castellon",
    "Ciudad Real",
    "Cordoba",
    "Cuenca",
    "Girona",
    "Granada",
    "Guadalajara",
    "Gipuzkoa",
    "Huelva",
    "Huesca",
    "Jaen",
    "La Rioja",
    "Las Palmas",
    "Leon",
    "Lleida",
    "Lugo",
    "Madrid",
    "Malaga",
    "Murcia",
    "Navarra",
    "Ourense",
    "Palencia",
    "Pontevedra",
    "Salamanca",
    "Segovia",
    "Sevilla",
    "Soria",
    "Tarragona",
    "Santa Cruz de Tenerife",
    "Teruel",
    "Toledo",
    "Valencia",
    "Valladolid",
    "Bizkaia",
    "Zamora",
    "Zaragoza",
    "Ceuta",
    "Melilla",
    "Balears",
    "Araba",
]

EXTRA_SEARCH_TERMS = [
    "sede",
    "oficina",
    "delegacion",
    "fabrica",
    "planta",
    "industrial",
    "produccion",
    "almacen",
    "logistica",
    "centro logistico",
    "laboratorio",
    "centro tecnologico",
    "I+D",
    "data center",
    "distribucion",
    "instalacion",
    "terminal",
    "puerto",
    "estacion",
    "headquarters",
    "factory",
    "warehouse",
]


def _unique_ordered(values: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        v = " ".join(value.split()).strip()
        if not v:
            continue
        key = v.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def _build_maps_queries(company_name: str) -> List[str]:
    budget = max(1, settings.MAPS_MAX_QUERY_BUDGET)

    category_keywords: List[str] = []
    per_category = max(1, settings.MAPS_KEYWORDS_PER_CATEGORY)
    for keywords in CATEGORY_SEARCH_KEYWORDS.values():
        category_keywords.extend(keywords[:per_category])

    discovery_terms = _unique_ordered(category_keywords + EXTRA_SEARCH_TERMS)
    base_queries: List[str] = [
        f'"{company_name}" Espana',
        f'"{company_name}" Spain',
        f'"{company_name}" empresa',
        f'"{company_name}"',
        f"{company_name} Espana",
        f"{company_name}",
    ]

    for term in discovery_terms:
        base_queries.append(f'"{company_name}" {term}')
        base_queries.append(f"{company_name} {term}")

    queries = _unique_ordered(base_queries)

    # Geographic expansion to improve recall for companies with distributed sites.
    for province in SPAIN_PROVINCES:
        if len(queries) >= budget:
            break
        queries.append(f'"{company_name}" {province}')
        if len(queries) >= budget:
            break
        queries.append(f"{company_name} {province} empresa")

    # Last expansion layer: targeted keyword+province combinations until we hit budget.
    if len(queries) < budget:
        for province in SPAIN_PROVINCES:
            for term in discovery_terms:
                if len(queries) >= budget:
                    break
                queries.append(f'"{company_name}" {term} {province}')
            if len(queries) >= budget:
                break

    final_queries = _unique_ordered(queries)[:budget]
    logger.info("Maps query plan for '%s': %s queries (budget=%s)", company_name, len(final_queries), budget)
    return final_queries

PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

SPAIN_LOCATION_BIAS = {
    "rectangle": {
        "low": {"latitude": 27.6, "longitude": -18.2},
        "high": {"latitude": 43.8, "longitude": 4.4},
    }
}

FIELDS = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.location,places.types,places.websiteUri,"
    "places.nationalPhoneNumber,places.rating,"
    "places.userRatingCount,places.businessStatus"
)


async def search_places_text(query: str, client: httpx.AsyncClient) -> List[dict]:
    headers = {
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": FIELDS,
        "Content-Type": "application/json",
    }
    body = {
        "textQuery": query,
        "locationBias": SPAIN_LOCATION_BIAS,
        "languageCode": "es",
        "maxResultCount": settings.MAPS_MAX_RESULTS_PER_QUERY,
    }
    try:
        resp = await client.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("places", [])
    except Exception as e:
        logger.warning(f"Places API error for query '{query}': {e}")
        return []


def parse_place(raw: dict) -> Optional[RawPlace]:
    try:
        loc = raw.get("location", {})
        return RawPlace(
            place_id=raw.get("id", ""),
            name=raw.get("displayName", {}).get("text", ""),
            address=raw.get("formattedAddress", ""),
            latitude=loc.get("latitude", 0),
            longitude=loc.get("longitude", 0),
            types=raw.get("types", []),
            website=raw.get("websiteUri"),
            phone=raw.get("nationalPhoneNumber"),
            rating=raw.get("rating"),
            user_ratings_total=raw.get("userRatingCount"),
            business_status=raw.get("businessStatus"),
        )
    except Exception as e:
        logger.warning(f"Failed to parse place: {e}")
        return None


async def search_company_assets(company_name: str) -> List[RawPlace]:
    queries = _build_maps_queries(company_name)
    executed_queries = len(queries)

    semaphore = asyncio.Semaphore(max(1, settings.MAPS_MAX_CONCURRENT_REQUESTS))
    all_places: List[dict] = []
    failed_queries = 0

    async with httpx.AsyncClient() as client:

        async def _search(q: str):
            async with semaphore:
                return await search_places_text(q, client)

        tasks = [_search(q) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_places.extend(result)
        else:
            failed_queries += 1

    seen = set()
    unique_places: List[RawPlace] = []
    for raw in all_places:
        place = parse_place(raw)
        if place and place.place_id and place.place_id not in seen:
            seen.add(place.place_id)
            unique_places.append(place)

    logger.info(
        "Maps discovery summary for '%s': queries_executed=%s raw_places=%s unique_place_ids=%s failed_queries=%s",
        company_name,
        executed_queries,
        len(all_places),
        len(unique_places),
        failed_queries,
    )
    return unique_places


async def search_company_candidates(query: str, limit: int = 10) -> List[dict]:
    headers = {
        "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.types,places.websiteUri",
        "Content-Type": "application/json",
    }
    body = {
        "textQuery": f"{query} empresa España",
        "locationBias": SPAIN_LOCATION_BIAS,
        "languageCode": "es",
        "maxResultCount": limit,
    }
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(PLACES_TEXT_SEARCH_URL, json=body, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.json().get("places", [])
        except Exception as e:
            logger.warning(f"Company search error: {e}")
            return []
