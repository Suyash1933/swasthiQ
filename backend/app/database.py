import os
import logging
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DB_PATH = BASE_DIR / "pharmacy.db"
DEFAULT_SQLITE_URL = f"sqlite:///{DB_PATH}"


def normalize_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return DEFAULT_SQLITE_URL

    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


REQUESTED_DATABASE_URL = normalize_database_url()
RUNNING_ON_RENDER = any(
    os.getenv(env_name)
    for env_name in ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_URL")
)
ALLOW_SQLITE_FALLBACK = os.getenv("ALLOW_SQLITE_FALLBACK", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str):
    engine_kwargs = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    elif database_url.startswith("postgresql+psycopg"):
        engine_kwargs["connect_args"] = {"connect_timeout": 5}
    return create_engine(database_url, **engine_kwargs)


def resolve_engine():
    primary_engine = build_engine(REQUESTED_DATABASE_URL)
    if REQUESTED_DATABASE_URL.startswith("sqlite"):
        return primary_engine, REQUESTED_DATABASE_URL, None

    try:
        with primary_engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return primary_engine, REQUESTED_DATABASE_URL, None
    except Exception as exc:
        primary_engine.dispose()
        fallback_allowed = ALLOW_SQLITE_FALLBACK and not RUNNING_ON_RENDER
        if not fallback_allowed:
            raise

        fallback_message = (
            "Configured PostgreSQL database is not reachable from this environment. "
            f"Falling back to local SQLite at {DB_PATH}. Original error: {exc}"
        )
        logger.warning(fallback_message)
        return build_engine(DEFAULT_SQLITE_URL), DEFAULT_SQLITE_URL, fallback_message


engine, DATABASE_URL, DATABASE_FALLBACK_REASON = resolve_engine()
DATABASE_LABEL = "postgresql" if DATABASE_URL.startswith("postgresql+psycopg") else "sqlite"
USING_SQLITE = DATABASE_URL.startswith("sqlite")
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
