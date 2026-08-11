"""FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, run_lightweight_migrations
from routers import assets, auth, users

# Apply small additive schema tweaks to an existing DB file without dropping
# it (see database.py), then create any missing tables (fine for
# SQLite/simple setups; use Alembic for real production migrations).
run_lightweight_migrations()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARC Asset Management & Barcode Generation")

# Allow the frontend (served from a different origin/port during development)
# to call this API with credentials/Authorization headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(assets.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
