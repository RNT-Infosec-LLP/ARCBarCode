"""SQLAlchemy ORM models for User and Asset."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    barcode_string = Column(String, unique=True, index=True, nullable=False)
    assigned_name = Column(String, nullable=False)
    serial_number = Column(String, unique=True, index=True, nullable=False)
    model = Column(String, nullable=True)
    make = Column(String, nullable=True)
    country = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True, index=True)
    asset_type = Column(String, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
