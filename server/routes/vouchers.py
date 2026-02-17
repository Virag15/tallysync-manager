"""
TallySync Manager — Vouchers Routes
Read cached vouchers synced from Tally Prime.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Company, VoucherCache
from models.schemas import VoucherResponse
from sync import sync_company

logger = logging.getLogger("tallysync.routes.vouchers")
router = APIRouter(prefix="/api/vouchers", tags=["vouchers"])


@router.get("", response_model=List[VoucherResponse])
def list_vouchers(
    company_id:   int           = Query(...),
    voucher_type: Optional[str] = Query(None),
    party_name:   Optional[str] = Query(None),
    from_date:    Optional[date] = Query(None),
    to_date:      Optional[date] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(VoucherCache).filter(VoucherCache.company_id == company_id)
    if voucher_type:
        q = q.filter(VoucherCache.voucher_type == voucher_type)
    if party_name:
        q = q.filter(VoucherCache.party_name.ilike(f"%{party_name}%"))
    if from_date:
        q = q.filter(VoucherCache.voucher_date >= from_date)
    if to_date:
        q = q.filter(VoucherCache.voucher_date <= to_date)

    return q.order_by(VoucherCache.voucher_date.desc()).offset(skip).limit(limit).all()


@router.get("/{voucher_id}", response_model=VoucherResponse)
def get_voucher(voucher_id: int, db: Session = Depends(get_db)):
    v = db.query(VoucherCache).filter(VoucherCache.id == voucher_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return v


@router.post("/sync")
async def sync_vouchers(
    company_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    background_tasks.add_task(sync_company, company_id)
    return {"message": "Voucher sync triggered", "company_id": company_id}


@router.get("/meta/types")
def voucher_types(company_id: int = Query(...), db: Session = Depends(get_db)):
    from sqlalchemy import distinct
    rows = (
        db.query(distinct(VoucherCache.voucher_type))
        .filter(VoucherCache.company_id == company_id)
        .all()
    )
    return [r[0] for r in rows if r[0]]
