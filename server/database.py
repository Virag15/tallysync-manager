"""
TallySync Manager — Database Setup (SQLAlchemy + SQLite)
"""

from __future__ import annotations

from sqlalchemy import create_engine, event, text as sqlalchemy_text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from config import DB_PATH, logger


DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

# Enable WAL mode for better concurrent read performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a DB session and closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables on startup, then run migrations."""
    from models import db_models  # noqa: F401 — ensure models are registered
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    logger.info("Database initialised at %s", DB_PATH)


# ─── Schema Version ────────────────────────────────────────────────────────────
# Increment SCHEMA_VERSION whenever a migration block is added below.
# SQLite's PRAGMA user_version stores this in the DB header (no extra tables).

SCHEMA_VERSION = 1


def _run_migrations() -> None:
    """Apply pending schema migrations and persist the new user_version.

    Rules:
    - Each migration block is guarded by  `if current_version < N`.
    - Blocks run in ascending order; PRAGMA user_version is written last.
    - All DDL uses IF NOT EXISTS / IF EXISTS — safe to re-run on a patched DB.
    """
    with engine.connect() as conn:
        current_version = conn.execute(
            sqlalchemy_text("PRAGMA user_version")
        ).scalar() or 0

        if current_version >= SCHEMA_VERSION:
            return  # already up-to-date

        logger.info(
            "Migrating database from schema v%d → v%d",
            current_version, SCHEMA_VERSION,
        )

        # ── v0 → v1 : composite indexes + unique constraints ──────────────────
        if current_version < 1:
            # Dedup before unique indexes in case a legacy DB has duplicate rows
            for stmt in [
                """DELETE FROM stock_items WHERE id NOT IN (
                     SELECT MAX(id) FROM stock_items GROUP BY company_id, tally_name)""",
                """DELETE FROM ledgers WHERE id NOT IN (
                     SELECT MAX(id) FROM ledgers GROUP BY company_id, tally_name)""",
            ]:
                try:
                    conn.execute(sqlalchemy_text(stmt))
                except Exception:
                    pass

            for stmt in [
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_company_name ON stock_items (company_id, tally_name)",
                "CREATE INDEX        IF NOT EXISTS ix_stock_company_group ON stock_items (company_id, group_name)",
                "CREATE INDEX        IF NOT EXISTS ix_stock_company_low   ON stock_items (company_id, is_low_stock)",
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_company_name ON ledgers (company_id, tally_name)",
                "CREATE INDEX        IF NOT EXISTS ix_ledger_company_group ON ledgers (company_id, group_name)",
                "CREATE INDEX        IF NOT EXISTS ix_ledger_company_type  ON ledgers (company_id, ledger_type)",
                "CREATE INDEX        IF NOT EXISTS ix_voucher_company_type_num ON voucher_cache (company_id, voucher_type, voucher_number)",
            ]:
                try:
                    conn.execute(sqlalchemy_text(stmt))
                except Exception:
                    pass  # index already exists — safe to skip

        # ── v1 → v2 : add your next migration here ────────────────────────────
        # if current_version < 2:
        #     conn.execute(sqlalchemy_text(
        #         "ALTER TABLE orders ADD COLUMN external_ref TEXT"
        #     ))

        conn.execute(sqlalchemy_text(f"PRAGMA user_version = {SCHEMA_VERSION}"))
        conn.commit()
        logger.info("Schema migration complete — now at v%d", SCHEMA_VERSION)
