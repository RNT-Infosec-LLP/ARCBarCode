# Asset Management & Barcode Generation

A minimal FastAPI application for tracking assets and generating printable
Code128 barcode stickers.

## Project structure

```
main.py            FastAPI app init, router includes
database.py         SQLAlchemy engine & SessionLocal
models.py            SQLAlchemy models (User, Asset)
schemas.py           Pydantic v2 request/response models
auth.py               JWT creation/verification, bcrypt hashing, get_current_user
barcode_utils.py      Barcode generation (python-barcode) + sticker composition (Pillow)
routers/
  auth.py             /auth/register, /auth/login
  assets.py           /assets CRUD, filtering, CSV upload, sticker generation
```

## Setup

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. (Optional) Set environment variables:

   - `SECRET_KEY` – JWT signing secret (set a strong random value in production)
   - `ORG_CODE` – short org code used in generated barcode strings (default `ARC`)
   - `ORG_NAME` – organization name shown on sticker header when no logo is present (default `ARC`)
   - `LOGO_PATH` – path to a logo image (PNG/JPG) to show on stickers instead of the text header

3. Run the app:

   ```powershell
   uvicorn main:app --reload
   ```

   The SQLite database file `arcbarcode.db` is created automatically on first run.

4. Open the interactive API docs at http://127.0.0.1:8000/docs

## Typical flow

1. `POST /auth/register` with `{"email": "...", "password": "..."}` to create your first user.
2. `POST /auth/login` with the same credentials to receive a JWT `access_token`.
3. Use the token as a Bearer token (`Authorization: Bearer <token>`) for all `/assets/*` endpoints.
4. `POST /assets` to create an asset (barcode_string is auto-generated if omitted).
5. `GET /assets?country=IND&city=KOL&page=1&page_size=20` to list/filter assets.
6. `POST /assets/upload-csv` with a CSV file (columns: `assigned_name`, `serial_number`, `model`, `make`, `country`, `city`, `asset_type`) for bulk import.
7. `GET /assets/{id}/generate-sticker` to download a PNG sticker with header + barcode.

## Notes

- Barcode string format: `{ORG_CODE}-{COUNTRY_CODE}-{CITY_CODE}-{TYPE_CODE}-{index}`, e.g. `ORG-IND-KOL-L-001`.
- Tables are created automatically via `Base.metadata.create_all` on startup; for schema changes in production, introduce a migration tool like Alembic.
