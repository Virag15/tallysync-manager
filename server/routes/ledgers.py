"""
TallySync Manager — Ledgers Routes
Read cached ledger (party) data from Tally.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Ledger
from models.schemas import LedgerResponse

logger = logging.getLogger("tallysync.routes.ledgers")
router = APIRouter(prefix="/api/ledgers", tags=["ledgers"])


@router.get("", response_model=List[LedgerResponse])
def list_ledgers(
    company_id:  int           = Query(...),
    ledger_type: Optional[str] = Query(None, pattern="^(CUSTOMER|SUPPLIER|OTHER)$"),
    search:      Optional[str] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(Ledger).filter(Ledger.company_id == company_id)
    if ledger_type:
        q = q.filter(Ledger.ledger_type == ledger_type)
    if search:
        q = q.filter(Ledger.tally_name.ilike(f"%{search}%"))
    return q.order_by(Ledger.tally_name).offset(skip).limit(limit).all()


@router.get("/{ledger_id}", response_model=LedgerResponse)
def get_ledger(ledger_id: int, db: Session = Depends(get_db)):
    ledger = db.query(Ledger).filter(Ledger.id == ledger_id).first()
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger not found")
    return ledger
