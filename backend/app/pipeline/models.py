from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AssetCategory(str, Enum):
    HQ = "HQ"
    OFF = "OFF"
    FAB = "FAB"
    LOG = "LOG"
    TEC = "TEC"
    COM = "COM"
    AGR = "AGR"
    ENE = "ENE"
    TRA = "TRA"
    HOT = "HOT"
    SAN = "SAN"
    OTR = "OTR"


CATEGORY_LABELS = {
    AssetCategory.HQ: "Sede Central",
    AssetCategory.OFF: "Oficina Regional",
    AssetCategory.FAB: "Fábrica / Planta Industrial",
    AssetCategory.LOG: "Centro Logístico",
    AssetCategory.TEC: "Centro Tecnológico",
    AssetCategory.COM: "Punto de Venta / Tienda",
    AssetCategory.AGR: "Explotación Agrícola / Ganadera",
    AssetCategory.ENE: "Instalación Energética",
    AssetCategory.TRA: "Infraestructura de Transporte",
    AssetCategory.HOT: "Activo Hotelero / Turístico",
    AssetCategory.SAN: "Centro Sanitario",
    AssetCategory.OTR: "Otro Activo Productivo",
}

CATEGORY_SEARCH_KEYWORDS = {
    AssetCategory.HQ: ["sede central", "headquarter", "dirección general", "oficinas centrales"],
    AssetCategory.OFF: ["oficina", "delegación", "sucursal"],
    AssetCategory.FAB: ["fábrica", "planta", "manufactura", "producción", "planta industrial"],
    AssetCategory.LOG: ["almacén", "logística", "distribución", "centro logístico", "nave logística"],
    AssetCategory.TEC: ["laboratorio", "I+D", "innovación", "data center", "centro tecnológico"],
    AssetCategory.COM: ["tienda", "punto de venta", "store", "supermercado"],
    AssetCategory.AGR: ["explotación", "finca", "granja", "explotación agrícola"],
    AssetCategory.ENE: ["planta solar", "parque eólico", "subestación", "central eléctrica"],
    AssetCategory.TRA: ["terminal", "puerto", "estación", "terminal logística"],
    AssetCategory.HOT: ["hotel", "resort", "complejo turístico"],
    AssetCategory.SAN: ["hospital", "clínica", "centro médico"],
    AssetCategory.OTR: [],
}


class CompanyInfo(BaseModel):
    id: str
    name: str
    cif: Optional[str] = None
    sector: Optional[str] = None
    cnae: Optional[str] = None
    logo_url: Optional[str] = None
    headquarters: Optional[str] = None


class RawPlace(BaseModel):
    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    types: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    business_status: Optional[str] = None


class FilteredAsset(BaseModel):
    place_id: str
    raw_name: str
    name: str
    category: AssetCategory
    is_productive_asset: bool = True
    is_headquarters: bool = False
    address: str
    latitude: float
    longitude: float
    types: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    llm_confidence: float = 0.5


class EnrichedAsset(FilteredAsset):
    description: Optional[str] = None
    size_estimate: Optional[str] = None
    functional_tags: List[str] = Field(default_factory=list)
    municipality: str = ""
    province: str = ""
    autonomous_community: str = ""
    postal_code: Optional[str] = None


class ScoredAsset(EnrichedAsset):
    confidence_score: float = 0.0
    confidence_tier: str = "LOW"
    data_sources: List[str] = Field(default_factory=lambda: ["maps_api", "llm_inference"])


class Asset(BaseModel):
    id: str
    company_id: str
    name: str
    raw_name: str
    category: AssetCategory
    subcategory: Optional[str] = None
    latitude: float
    longitude: float
    address: str
    municipality: str = ""
    province: str = ""
    autonomous_community: str = ""
    postal_code: Optional[str] = None
    description: Optional[str] = None
    size_estimate: Optional[str] = None
    functional_tags: List[str] = Field(default_factory=list)
    is_headquarters: bool = False
    google_place_id: str
    confidence_score: float = 0.0
    confidence_tier: str = "LOW"
    data_sources: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyzeRequest(BaseModel):
    company_id: str
    company_name: str
    force_refresh: bool = False


class DocumentAnalyzeRequest(BaseModel):
    company_name: Optional[str] = None
    force_refresh: bool = False


class DocumentExtractedAsset(BaseModel):
    asset_name: str
    category: AssetCategory = AssetCategory.OTR
    location_hints: List[str] = Field(default_factory=list)
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    evidence_quote: Optional[str] = None
    llm_confidence: float = 0.5
    source_chunk: Optional[int] = None


class DocumentEnrichedAsset(DocumentExtractedAsset):
    place_id: str
    raw_name: str
    name: str
    latitude: float
    longitude: float
    address: str
    types: List[str] = Field(default_factory=list)
    website: Optional[str] = None
    phone: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    is_headquarters: bool = False
    description: Optional[str] = None
    size_estimate: Optional[str] = None
    functional_tags: List[str] = Field(default_factory=list)
    municipality: str = ""
    province: str = ""
    autonomous_community: str = ""
    postal_code: Optional[str] = None
    coordinate_source: str = "unknown"
    evidence_count: int = 1


class DocumentScoredAsset(DocumentEnrichedAsset):
    confidence_score: float = 0.0
    confidence_tier: str = "LOW"
    data_sources: List[str] = Field(default_factory=lambda: ["document_upload", "llm_inference"])


class AgentFoundFile(BaseModel):
    filename: str
    size: int
    url: str
    relevance_reason: str


class AgentSearchRequest(BaseModel):
    company_name: str
    company_id: str


class PipelineEvent(BaseModel):
    event: str
    data: dict
