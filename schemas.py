"""Pydantic v2 schemas for request/response validation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Asset schemas
# ---------------------------------------------------------------------------
class AssetBase(BaseModel):
    assigned_name: Optional[str] = None
    serial_number: str
    model: Optional[str] = None
    make: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    asset_type: Optional[str] = None


class AssetCreate(AssetBase):
    # Optional: if not provided, it is auto-generated from org/country/city/type/index.
    barcode_string: Optional[str] = None


class AssetUpdate(BaseModel):
    assigned_name: Optional[str] = None
    serial_number: Optional[str] = None
    model: Optional[str] = None
    make: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    asset_type: Optional[str] = None
    barcode_string: Optional[str] = None


class AssetOut(AssetBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    barcode_string: str
    created_at: datetime


class AssetPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AssetOut]


class CSVUploadResult(BaseModel):
    inserted: int
    skipped: int
    errors: list[str]
