"""
TallySync Manager — Inventory Routes
Read-only access to cached stock items from Tally.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import StockItem
from models.schemas import StockItemResponse, StockStats

logger = logging.getLogger("tallysync.routes.inventory")
router = APIRouter(prefix="/api/inventory", tags=["inventory"])


# ─── List Stock Items ─────────────────────────────────────────────────────────

@router.get("", response_model=List[StockItemResponse])
def list_stock_items(
    company_id: int     = Query(..., description="Filter by company"),
    search:     Optional[str] = Query(None),
    group:      Optional[str] = Query(None),
    low_stock:  bool          = Query(False),
    skip:       int           = Query(0, ge=0),
    limit:      int           = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    q = db.query(StockItem).filter(StockItem.company_id == company_id)

    if search:
        pattern = f"%{search}%"
        q = q.filter(
            StockItem.tally_name.ilike(pattern) | StockItem.alias.ilike(pattern)
        )
    if group:
        q = q.filter(StockItem.group_name == group)
    if low_stock:
        q = q.filter(StockItem.is_low_stock == True)

    return q.order_by(StockItem.tally_name).offset(skip).limit(limit).all()


# ─── Single Item ──────────────────────────────────────────────────────────────

@router.get("/{item_id}", response_model=StockItemResponse)
def get_stock_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(StockItem).filter(StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return item


# ─── Groups ──────────────────────────────────────────────────────────────────

@router.get("/meta/groups", response_model=List[str])
def list_groups(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(distinct(StockItem.group_name))
        .filter(StockItem.company_id == company_id, StockItem.group_name.isnot(None))
        .order_by(StockItem.group_name)
        .all()
    )
    return [r[0] for r in rows]


# ─── Stats ───────────────────────────────────────────────────────────────────

@router.get("/meta/stats", response_model=StockStats)
def get_stock_stats(company_id: int = Query(...), db: Session = Depends(get_db)):
    total_items = db.query(func.count(StockItem.id)).filter(StockItem.company_id == company_id).scalar()
    low_stock_count = (
        db.query(func.count(StockItem.id))
        .filter(StockItem.company_id == company_id, StockItem.is_low_stock == True)
        .scalar()
    )
    total_value = (
        db.query(func.coalesce(func.sum(StockItem.closing_value), 0.0))
        .filter(StockItem.company_id == company_id)
        .scalar()
    )
    groups = [
        r[0]
        for r in db.query(distinct(StockItem.group_name))
        .filter(StockItem.company_id == company_id, StockItem.group_name.isnot(None))
        .order_by(StockItem.group_name)
        .all()
    ]
    return StockStats(
        total_items=total_items or 0,
        low_stock_count=low_stock_count or 0,
        total_value=round(total_value or 0.0, 2),
        groups=groups,
    )


# ─── Update Reorder Level ─────────────────────────────────────────────────────

@router.patch("/{item_id}/reorder-level")
def set_reorder_level(
    item_id: int,
    reorder_level: float = Query(..., ge=0),
    db: Session = Depends(get_db),
):
    item = db.query(StockItem).filter(StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    item.reorder_level = reorder_level
    item.is_low_stock  = item.closing_qty <= reorder_level and reorder_level > 0
    db.commit()
    return {"id": item_id, "reorder_level": reorder_level, "is_low_stock": item.is_low_stock}
