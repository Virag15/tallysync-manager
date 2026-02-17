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
    """Pull stock items, upsert into SQLite, return record count."""
    items = await client.fetch_stock_items(company.tally_company_name)
    now = datetime.utcnow()

    # Build lookup for existing items
    existing = {
        s.tally_name: s
        for s in db.query(StockItem).filter(StockItem.company_id == company.id).all()
    }

    count = 0
    for item_data in items:
        name = item_data["tally_name"]
        if name in existing:
            obj = existing[name]
        else:
            obj = StockItem(company_id=company.id, tally_name=name)
            db.add(obj)

        obj.alias         = item_data.get("alias")
        obj.group_name    = item_data.get("group_name")
        obj.uom           = item_data.get("uom")
        obj.closing_qty   = item_data.get("closing_qty", 0.0)
        obj.closing_value = item_data.get("closing_value", 0.0)
        obj.rate          = item_data.get("rate", 0.0)
        reorder = obj.reorder_level or 0
        obj.is_low_stock  = reorder > 0 and obj.closing_qty <= reorder
        obj.last_synced_at = now
        count += 1

    db.flush()
    return count


async def _sync_ledgers(db: Session, company: Company, client: TallyClient) -> int:
    """Pull ledgers, upsert into SQLite, return record count."""
    ledgers = await client.fetch_ledgers(company.tally_company_name)
    now = datetime.utcnow()

    existing = {
        l.tally_name: l
        for l in db.query(Ledger).filter(Ledger.company_id == company.id).all()
    }

    count = 0
    for ledger_data in ledgers:
        name = ledger_data["tally_name"]
        if name in existing:
            obj = existing[name]
        else:
            obj = Ledger(company_id=company.id, tally_name=name)
            db.add(obj)

        obj.alias           = ledger_data.get("alias")
        obj.group_name      = ledger_data.get("group_name")
        obj.ledger_type     = ledger_data.get("ledger_type")
        obj.opening_balance = ledger_data.get("opening_balance", 0.0)
        obj.closing_balance = ledger_data.get("closing_balance", 0.0)
        obj.last_synced_at  = now
        count += 1

    db.flush()
    return count


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
