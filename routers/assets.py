"""Asset CRUD, filtering/pagination, CSV bulk upload, and sticker generation."""
import csv
import io
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_current_user
from barcode_utils import generate_sticker
from database import get_db
from models import Asset
from schemas import AssetCreate, AssetOut, AssetPage, AssetUpdate, CSVUploadResult

router = APIRouter(prefix="/assets", tags=["assets"])

ORG_CODE = os.environ.get("ORG_CODE", "ARC")

# Short codes used inside the auto-generated barcode string.
def _code(value: Optional[str], length: int = 3) -> str:
    return (value or "GEN").strip().upper()[:length] or "GEN"


def _generate_barcode_string(
    db: Session,
    country: str,
    city: str,
    asset_type: str,
    prefix_counters: Optional[dict] = None,
) -> str:
    """Build a barcode string like ARC-IND-KOL-L-001, unique per country/city/type.

    ``prefix_counters`` is an optional in-memory cache (shared across rows within
    a single request, e.g. a CSV bulk upload) mapping prefix -> next free index.
    This avoids relying on DB queries to "see" rows already added but not yet
    flushed/committed in the current session (the session uses autoflush=False),
    which would otherwise let multiple rows in the same batch collide on the
    same generated barcode string.
    """
    prefix = f"{ORG_CODE}-{_code(country)}-{_code(city)}-{_code(asset_type, 1)}"

    if prefix_counters is None:
        prefix_counters = {}

    if prefix not in prefix_counters:
        existing_count = (
            db.query(Asset).filter(Asset.barcode_string.like(f"{prefix}-%")).count()
        )
        prefix_counters[prefix] = existing_count

    index = prefix_counters[prefix] + 1
    candidate = f"{prefix}-{index:03d}"
    # Guard against rare collisions (e.g. manually inserted barcode strings).
    while db.query(Asset).filter(Asset.barcode_string == candidate).first():
        index += 1
        candidate = f"{prefix}-{index:03d}"

    prefix_counters[prefix] = index
    return candidate


# ---------------------------------------------------------------------------
# CRUD + listing
# ---------------------------------------------------------------------------
@router.get("", response_model=AssetPage)
def list_assets(
    item_no: Optional[int] = Query(None, description="Filter by asset id"),
    serial_number: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    query = db.query(Asset)

    if item_no is not None:
        query = query.filter(Asset.id == item_no)
    if serial_number:
        query = query.filter(Asset.serial_number.ilike(f"%{serial_number}%"))
    if country:
        query = query.filter(Asset.country.ilike(f"%{country}%"))
    if city:
        query = query.filter(Asset.city.ilike(f"%{city}%"))
    if asset_type:
        query = query.filter(Asset.asset_type.ilike(f"%{asset_type}%"))

    total = query.count()
    items = (
        query.order_by(Asset.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AssetPage(total=total, page=page, page_size=page_size, items=items)


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
def create_asset(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if db.query(Asset).filter(Asset.serial_number == asset_in.serial_number).first():
        raise HTTPException(status_code=400, detail="Serial number already exists")

    barcode_string = asset_in.barcode_string or _generate_barcode_string(
        db, asset_in.country, asset_in.city, asset_in.asset_type
    )
    if db.query(Asset).filter(Asset.barcode_string == barcode_string).first():
        raise HTTPException(status_code=400, detail="Barcode string already exists")

    asset = Asset(**asset_in.model_dump(exclude={"barcode_string"}), barcode_string=barcode_string)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.put("/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    updates = asset_in.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(asset, field, value)

    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(asset)
    db.commit()


# ---------------------------------------------------------------------------
# Bulk CSV upload
# ---------------------------------------------------------------------------
REQUIRED_CSV_FIELDS = [
    "assigned_name",
    "serial_number",
    "model",
    "make",
    "country",
    "city",
    "asset_type",
]


@router.post("/upload-csv", response_model=CSVUploadResult)
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    raw = file.file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))

    missing_columns = [f for f in REQUIRED_CSV_FIELDS if f not in (reader.fieldnames or [])]
    if missing_columns:
        raise HTTPException(
            status_code=400, detail=f"CSV missing required columns: {missing_columns}"
        )

    inserted = 0
    skipped = 0
    errors: list[str] = []
    new_assets: list[Asset] = []
    seen_serials: set[str] = set()
    prefix_counters: dict = {}

    for row_number, row in enumerate(reader, start=2):  # header is row 1
        try:
            asset_in = AssetCreate(**{field: row.get(field) or None for field in REQUIRED_CSV_FIELDS})
        except ValidationError as exc:
            skipped += 1
            errors.append(f"Row {row_number}: {exc.errors()[0]['msg']}")
            continue

        if asset_in.serial_number in seen_serials or db.query(Asset).filter(
            Asset.serial_number == asset_in.serial_number
        ).first():
            skipped += 1
            errors.append(f"Row {row_number}: serial_number already exists")
            continue

        barcode_string = _generate_barcode_string(
            db, asset_in.country, asset_in.city, asset_in.asset_type, prefix_counters
        )
        asset = Asset(**asset_in.model_dump(exclude={"barcode_string"}), barcode_string=barcode_string)
        db.add(asset)
        new_assets.append(asset)
        seen_serials.add(asset_in.serial_number)
        inserted += 1

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Bulk upload failed due to a duplicate serial number or barcode. No rows were inserted.",
        )
    return CSVUploadResult(inserted=inserted, skipped=skipped, errors=errors)


# ---------------------------------------------------------------------------
# Barcode sticker image
# ---------------------------------------------------------------------------
@router.get("/{asset_id}/generate-sticker")
def generate_sticker_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    image_stream = generate_sticker(asset.barcode_string)
    return StreamingResponse(image_stream, media_type="image/png")
