"""SQLAlchemy engine & session setup (SQLite)."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite database file lives next to this file.
SQLALCHEMY_DATABASE_URL = "sqlite:///./arcbarcode.db"

# check_same_thread=False is required for SQLite when used with FastAPI's
# threaded request handling.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_lightweight_migrations():
    """
    Apply small, additive schema tweaks to an existing SQLite DB without
    dropping/recreating tables (which would destroy existing data).

    SQLite can't directly alter a column's NOT NULL constraint, so for that
    specific case we rebuild the table via the documented 12-step process
    (create new table, copy data, drop old, rename) instead of wiping the file.

    NOTE: this is a pragmatic stand-in for a real migration tool. For
    anything beyond simple nullability tweaks, use Alembic.
    """
    inspector = inspect(engine)
    if "assets" not in inspector.get_table_names():
        return  # fresh DB — create_all() will set it up correctly.

    columns = {col["name"]: col for col in inspector.get_columns("assets")}
    assigned_name_col = columns.get("assigned_name")
    if assigned_name_col is not None and not assigned_name_col["nullable"]:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE assets RENAME TO assets_old"))
            Base.metadata.tables["assets"].create(bind=conn)
            conn.execute(
                text(
                    """
                    INSERT INTO assets (
                        id, barcode_string, assigned_name, serial_number,
                        model, make, country, city, asset_type, created_at
                    )
                    SELECT
                        id, barcode_string, assigned_name, serial_number,
                        model, make, country, city, asset_type, created_at
                    FROM assets_old
                    """
                )
            )
            conn.execute(text("DROP TABLE assets_old"))

    # Account lockout policy columns on users — SQLite supports ADD COLUMN
    # directly, so no table rebuild is needed for these.
    if "users" in inspector.get_table_names():
        user_columns = {col["name"] for col in inspector.get_columns("users")}
        with engine.begin() as conn:
            if "failed_login_attempts" not in user_columns:
                conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN failed_login_attempts "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
            if "locked_until" not in user_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN locked_until DATETIME"))
