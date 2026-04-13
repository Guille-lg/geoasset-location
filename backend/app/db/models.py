from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class AssetRecord(Base):
    __tablename__ = "assets"

    id = Column(String, primary_key=True)
    company_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    raw_name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text, nullable=False)
    municipality = Column(String, default="")
    province = Column(String, default="")
    autonomous_community = Column(String, default="")
    postal_code = Column(String, nullable=True)

    description = Column(Text, nullable=True)
    size_estimate = Column(String, nullable=True)
    functional_tags = Column(ARRAY(String), default=[])
    is_headquarters = Column(Boolean, default=False)

    google_place_id = Column(String, nullable=False)
    confidence_score = Column(Float, default=0.0)
    confidence_tier = Column(String, default="LOW")
    data_sources = Column(ARRAY(String), default=[])

    website = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyRecord(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    cif = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    cnae = Column(String, nullable=True)
    headquarters = Column(String, nullable=True)
    last_analyzed_at = Column(DateTime, nullable=True)
    total_assets = Column(Integer, default=0)
