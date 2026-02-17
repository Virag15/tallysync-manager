"""
TallySync Manager — Companies Routes
CRUD for Tally host configurations + connection testing + manual sync trigger.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Company, SyncLog, StockItem, Ledger
from models.schemas import (
    CompanyCreate, CompanyUpdate, CompanyResponse,
    ConnectionTestResult, SyncLogResponse, PushResult,
)
from sync import sync_company, schedule_company, remove_company_schedule
from tally.xml_builder import OrderLineData
from tally_client import TallyClient

logger = logging.getLogger("tallysync.routes.companies")
router = APIRouter(prefix="/api/companies", tags=["companies"])


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[CompanyResponse])
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).order_by(Company.name).all()


# ─── Get by ID ───────────────────────────────────────────────────────────────

@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


# ─── Create ──────────────────────────────────────────────────────────────────

@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    company = Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    # Start scheduling syncs for this company
    schedule_company(company.id, company.sync_interval_minutes)
    logger.info("Created company '%s' (id=%d)", company.name, company.id)
    return company


# ─── Update ──────────────────────────────────────────────────────────────────

@router.put("/{company_id}", response_model=CompanyResponse)
def update_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = payload.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    db.commit()
    db.refresh(company)

    # Reschedule if interval changed or active status changed
    if company.is_active:
        schedule_company(company.id, company.sync_interval_minutes)
    else:
        remove_company_schedule(company.id)

    logger.info("Updated company %d", company_id)
    return company


# ─── Delete ──────────────────────────────────────────────────────────────────

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    remove_company_schedule(company_id)
    db.delete(company)
    db.commit()
    logger.info("Deleted company %d", company_id)


# ─── Test Connection ──────────────────────────────────────────────────────────

@router.post("/{company_id}/test-connection", response_model=ConnectionTestResult)
async def test_connection(company_id: int, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    client = TallyClient(company.host, company.port)
    success, message, open_companies = await client.test_connection()
    return ConnectionTestResult(
        success=success,
        message=message,
        open_companies=open_companies,
    )


# ─── Manual Sync Trigger ──────────────────────────────────────────────────────

@router.post("/{company_id}/sync")
async def trigger_sync(
    company_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    background_tasks.add_task(sync_company, company_id)
    return {"message": f"Sync triggered for '{company.name}'", "company_id": company_id}


# ─── Sync Logs ────────────────────────────────────────────────────────────────

@router.get("/{company_id}/sync-logs", response_model=List[SyncLogResponse])
def get_sync_logs(company_id: int, limit: int = 20, db: Session = Depends(get_db)):
    logs = (
        db.query(SyncLog)
        .filter(SyncLog.company_id == company_id)
        .order_by(SyncLog.started_at.desc())
        .limit(limit)
        .all()
    )
    return logs


# ─── Test Entry ───────────────────────────────────────────────────────────────

@router.post("/{company_id}/test-entry", response_model=PushResult)
async def test_entry(company_id: int, db: Session = Depends(get_db)):
    """
    Push a minimal test Sales Order voucher to Tally using the first available
    synced stock item and customer ledger.  The voucher is clearly labelled so
    it can be deleted from Tally after verification.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Need at least one synced stock item
    stock_item = (
        db.query(StockItem)
        .filter(StockItem.company_id == company_id, StockItem.closing_qty > 0)
        .first()
        or db.query(StockItem).filter(StockItem.company_id == company_id).first()
    )
    if not stock_item:
        raise HTTPException(
            status_code=400,
            detail="No stock items found. Run a sync first so TallySync knows your items.",
        )

    # Prefer a CUSTOMER ledger; fall back to any ledger
    ledger = (
        db.query(Ledger)
        .filter(Ledger.company_id == company_id, Ledger.ledger_type == "CUSTOMER")
        .first()
        or db.query(Ledger).filter(Ledger.company_id == company_id).first()
    )
    if not ledger:
        raise HTTPException(
            status_code=400,
            detail="No ledgers found. Run a sync first so TallySync knows your parties.",
        )

    rate = max(stock_item.rate, 1.0)
    line = OrderLineData(
        stock_item_name=stock_item.tally_name,
        quantity=1.0,
        rate=rate,
        amount=rate,
        uom=stock_item.uom or "Nos",
        is_sales=True,
    )

    client = TallyClient(company.host, company.port)
    order_number = f"TSYNC-TEST-{date.today().strftime('%Y%m%d')}"
    success, message, voucher_number = await client.push_sales_order(
        company_name=company.tally_company_name,
        order_number=order_number,
        order_date=date.today(),
        party_name=ledger.tally_name,
        lines=[line],
        narration="TallySync Manager test entry — safe to delete after verification",
    )
    logger.info(
        "Test entry for company %d: success=%s voucher=%s", company_id, success, voucher_number
    )
    return PushResult(success=success, message=message, tally_voucher_number=voucher_number)
