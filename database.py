"""SQLAlchemy engine & session setup (SQLite)."""
from sqlalchemy import create_engine
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
