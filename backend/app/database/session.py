import os
import logging
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings, BASE_DIR

logger = logging.getLogger("nexora.database")

def get_normalized_database_url(raw_url: str) -> str:
    """
    Normalizes PostgreSQL and SQLite URLs for SQLAlchemy 2.0 and Supabase.
    """
    url = raw_url.strip() if raw_url else "sqlite:///nexora_ja_assure.db"

    # Normalize Supabase / PostgreSQL URLs
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # SQLite resolution
    if url.startswith("sqlite:///"):
        sqlite_path = url.replace("sqlite:///", "")
        if not os.path.isabs(sqlite_path):
            resolved_path = (BASE_DIR / sqlite_path).resolve()
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            url = f"sqlite:///{resolved_path.as_posix()}"
        else:
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    return url

db_url = get_normalized_database_url(settings.DATABASE_URL)
is_sqlite = "sqlite" in db_url
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "echo": False,
    "connect_args": connect_args,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_engine(db_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
