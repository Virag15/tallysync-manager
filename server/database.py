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
    """Create all tables on startup, then run index migrations."""
    from models import db_models  # noqa: F401 — ensure models are registered
    Base.metadata.create_all(bind=engine)
    _run_index_migrations()
    logger.info("Database initialised at %s", DB_PATH)


def _run_index_migrations() -> None:
    """Idempotent: create composite indexes on existing databases that predate __table_args__."""
    stmts = [
        # stock_items composite indexes
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_company_name      ON stock_items (company_id, tally_name)",
        "CREATE INDEX        IF NOT EXISTS ix_stock_company_group      ON stock_items (company_id, group_name)",
        "CREATE INDEX        IF NOT EXISTS ix_stock_company_low        ON stock_items (company_id, is_low_stock)",
        "CREATE INDEX        IF NOT EXISTS ix_stock_company_name_srch  ON stock_items (company_id, tally_name)",
        # ledgers composite indexes
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_company_name      ON ledgers (company_id, tally_name)",
        "CREATE INDEX        IF NOT EXISTS ix_ledger_company_group      ON ledgers (company_id, group_name)",
        "CREATE INDEX        IF NOT EXISTS ix_ledger_company_type       ON ledgers (company_id, ledger_type)",
        "CREATE INDEX        IF NOT EXISTS ix_ledger_company_name_srch  ON ledgers (company_id, tally_name)",
        # voucher_cache lookup index
        "CREATE INDEX IF NOT EXISTS ix_voucher_company_type_num ON voucher_cache (company_id, voucher_type, voucher_number)",
    ]
    with engine.connect() as conn:
        for stmt in stmts:
            try:
                conn.execute(sqlalchemy_text(stmt))
            except Exception:
                pass  # index may already exist under a different name
        conn.commit()


