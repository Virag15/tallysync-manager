"""
TallySync Manager — Sync Engine (APScheduler + SQLite cache update)
Pulls data from Tally on a schedule and broadcasts SSE events when done.
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from events_manager import events_manager
from models.db_models import Company, StockItem, Ledger, VoucherCache, SyncLog
from tally_client import TallyClient

logger = logging.getLogger("tallysync.sync")

scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


# ─── Core Sync Logic ─────────────────────────────────────────────────────────

async def sync_company(company_id: int) -> None:
    """Full sync for one company: stock items + ledgers + recent vouchers."""
    db: Session = SessionLocal()
    started_at = datetime.utcnow()
    total_records = 0

    try:
        company: Optional[Company] = db.query(Company).filter(
            Company.id == company_id, Company.is_active == True
        ).first()

        if not company:
            logger.warning("sync_company: company %d not found or inactive", company_id)
            return

        logger.info("Starting sync for company '%s' (%s:%d)", company.name, company.host, company.port)
        client = TallyClient(company.host, company.port)

        # ── 1. Stock Items ────────────────────────────────────────────────────
        stock_records = await _sync_stock(db, company, client)
        total_records += stock_records

        # ── 2. Ledgers ────────────────────────────────────────────────────────
        ledger_records = await _sync_ledgers(db, company, client)
        total_records += ledger_records

        # ── 3. Recent Vouchers (last 30 days) ─────────────────────────────────
        voucher_records = await _sync_vouchers(db, company, client)
        total_records += voucher_records

        # ── Update company last_synced_at ──────────────────────────────────────
        company.last_synced_at = datetime.utcnow()
        db.commit()

        duration = (datetime.utcnow() - started_at).total_seconds()
        _log_sync(db, company_id, "FULL", "SUCCESS", total_records, None, started_at, duration)
        db.commit()

        logger.info(
            "Sync complete for '%s': %d records in %.1fs",
            company.name, total_records, duration,
        )

        await events_manager.broadcast(
            "sync_complete",
            {
                "company_id":   company_id,
                "company_name": company.name,
                "records":      total_records,
                "synced_at":    company.last_synced_at.isoformat(),
                "duration_s":   round(duration, 2),
            },
            company_id=company_id,
        )

    except Exception as exc:
        duration = (datetime.utcnow() - started_at).total_seconds()
        logger.exception("Sync failed for company %d: %s", company_id, exc)
        _log_sync(db, company_id, "FULL", "FAILED", total_records, str(exc), started_at, duration)
        db.commit()

        await events_manager.broadcast(
            "sync_error",
            {"company_id": company_id, "error": str(exc)},
            company_id=company_id,
        )
    finally:
        db.close()


async def _sync_stock(db: Session, company: Company, client: TallyClient) -> int:
    """Pull stock items, batch-upsert into SQLite, return record count.

    Uses raw SQL executemany instead of ORM objects — ~100x faster for 100K rows.
    Preserves user-set reorder_level values (not overwritten by Tally data).
    """
    items = await client.fetch_stock_items(company.tally_company_name)
    if not items:
        return 0

    now = datetime.utcnow().isoformat()

    # Fetch only the columns we need to preserve (reorder_level is user-managed)
    rows = db.execute(
        text("SELECT tally_name, reorder_level FROM stock_items WHERE company_id = :cid"),
        {"cid": company.id},
    ).fetchall()
    reorder_map: dict[str, float] = {r[0]: (r[1] or 0.0) for r in rows}

    batch = []
    for item_data in items:
        name    = item_data["tally_name"]
        qty     = float(item_data.get("closing_qty", 0.0))
        reorder = reorder_map.get(name, 0.0)
        batch.append({
            "company_id":    company.id,
            "tally_name":    name,
            "alias":         item_data.get("alias"),
            "group_name":    item_data.get("group_name"),
            "uom":           item_data.get("uom"),
            "closing_qty":   qty,
            "closing_value": float(item_data.get("closing_value", 0.0)),
            "rate":          float(item_data.get("rate", 0.0)),
            "reorder_level": reorder,
            "is_low_stock":  1 if (reorder > 0 and qty <= reorder) else 0,
            "last_synced_at": now,
        })

    # Single batch upsert — ON CONFLICT uses the unique index (company_id, tally_name)
    # Reorder level is preserved: only updated if the incoming value is > 0
    db.execute(
        text("""
            INSERT INTO stock_items
                (company_id, tally_name, alias, group_name, uom,
                 closing_qty, closing_value, rate, reorder_level,
                 is_low_stock, last_synced_at)
            VALUES
                (:company_id, :tally_name, :alias, :group_name, :uom,
                 :closing_qty, :closing_value, :rate, :reorder_level,
                 :is_low_stock, :last_synced_at)
            ON CONFLICT(company_id, tally_name) DO UPDATE SET
                alias          = excluded.alias,
                group_name     = excluded.group_name,
                uom            = excluded.uom,
                closing_qty    = excluded.closing_qty,
                closing_value  = excluded.closing_value,
                rate           = excluded.rate,
                reorder_level  = CASE
                                   WHEN stock_items.reorder_level > 0
                                   THEN stock_items.reorder_level
                                   ELSE excluded.reorder_level
                                 END,
                is_low_stock   = CASE
                                   WHEN stock_items.reorder_level > 0
                                   THEN (excluded.closing_qty <= stock_items.reorder_level)
                                   ELSE 0
                                 END,
                last_synced_at = excluded.last_synced_at
        """),
        batch,
    )
    db.commit()
    return len(batch)


async def _sync_ledgers(db: Session, company: Company, client: TallyClient) -> int:
    """Pull ledgers, batch-upsert into SQLite, return record count."""
    ledgers = await client.fetch_ledgers(company.tally_company_name)
    if not ledgers:
        return 0

    now = datetime.utcnow().isoformat()

    batch = [
        {
            "company_id":      company.id,
            "tally_name":      ld["tally_name"],
            "alias":           ld.get("alias"),
            "group_name":      ld.get("group_name"),
            "ledger_type":     ld.get("ledger_type"),
            "opening_balance": float(ld.get("opening_balance", 0.0)),
            "closing_balance": float(ld.get("closing_balance", 0.0)),
            "last_synced_at":  now,
        }
        for ld in ledgers
    ]

    db.execute(
        text("""
            INSERT INTO ledgers
                (company_id, tally_name, alias, group_name, ledger_type,
                 opening_balance, closing_balance, last_synced_at)
            VALUES
                (:company_id, :tally_name, :alias, :group_name, :ledger_type,
                 :opening_balance, :closing_balance, :last_synced_at)
            ON CONFLICT(company_id, tally_name) DO UPDATE SET
                alias           = excluded.alias,
                group_name      = excluded.group_name,
                ledger_type     = excluded.ledger_type,
                opening_balance = excluded.opening_balance,
                closing_balance = excluded.closing_balance,
                last_synced_at  = excluded.last_synced_at
        """),
        batch,
    )
    db.commit()
    return len(batch)


async def _sync_vouchers(db: Session, company: Company, client: TallyClient) -> int:
    """Pull recent sales and purchase order vouchers, upsert into cache."""
    now = datetime.utcnow()
    count = 0

    for vtype in ("Sales Order", "Purchase Order"):
        try:
            vouchers = await client.fetch_vouchers(
                company.tally_company_name, vtype, days_back=30
            )
            for v in vouchers:
                vnum = v.get("voucher_number")
                if not vnum:
                    continue
                existing = db.query(VoucherCache).filter(
                    VoucherCache.company_id == company.id,
                    VoucherCache.voucher_number == vnum,
                    VoucherCache.voucher_type == vtype,
                ).first()
                if not existing:
                    existing = VoucherCache(
                        company_id=company.id,
                        voucher_number=vnum,
                        voucher_type=vtype,
                    )
                    db.add(existing)
                existing.voucher_date  = v.get("voucher_date")
                existing.party_name    = v.get("party_name")
                existing.narration     = v.get("narration")
                existing.amount        = v.get("amount", 0.0)
                existing.last_synced_at = now
                count += 1
        except Exception as exc:
            logger.warning("Could not sync '%s' vouchers for '%s': %s", vtype, company.name, exc)

    db.flush()
    return count


def _log_sync(
    db: Session,
    company_id: int,
    sync_type: str,
    status: str,
    records: int,
    error: Optional[str],
    started_at: datetime,
    duration: float,
) -> None:
    log = SyncLog(
        company_id=company_id,
        sync_type=sync_type,
        status=status,
        records_synced=records,
        error_message=error,
        started_at=started_at,
        completed_at=datetime.utcnow(),
        duration_seconds=round(duration, 2),
    )
    db.add(log)


# ─── Scheduler Management ─────────────────────────────────────────────────────

def schedule_company(company_id: int, interval_minutes: int) -> None:
    """Add or replace a scheduled job for a company."""
    job_id = f"sync_company_{company_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        sync_company,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id=job_id,
        args=[company_id],
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        name=f"Sync company {company_id}",
    )
    logger.info("Scheduled sync for company %d every %d min(s)", company_id, interval_minutes)


def remove_company_schedule(company_id: int) -> None:
    job_id = f"sync_company_{company_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info("Removed sync schedule for company %d", company_id)


def start_scheduler(db: Session) -> None:
    """Load all active companies and schedule their syncs."""
    companies = db.query(Company).filter(Company.is_active == True).all()
    for company in companies:
        schedule_company(company.id, company.sync_interval_minutes)

    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started with %d job(s)", len(companies))
