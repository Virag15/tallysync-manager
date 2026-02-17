"""
TallySync Manager — Reports Routes
Aggregated analytics from the local SQLite cache.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Company, Order, OrderItem, StockItem, Ledger, VoucherCache
from models.schemas import DashboardKPI, StockMovementItem, PartyOutstanding

logger = logging.getLogger("tallysync.routes.reports")
router = APIRouter(prefix="/api/reports", tags=["reports"])


# ─── Dashboard KPIs ───────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardKPI)
def dashboard_kpi(company_id: int = Query(...), db: Session = Depends(get_db)):
    today = date.today()

    orders_today = (
        db.query(func.count(Order.id))
        .filter(Order.company_id == company_id, Order.order_date == today)
        .scalar() or 0
    )
    sales_today = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0.0))
        .filter(
            Order.company_id == company_id,
            Order.order_type == "SALES",
            Order.order_date == today,
            Order.status != "CANCELLED",
        )
        .scalar() or 0.0
    )
    purchase_today = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0.0))
        .filter(
            Order.company_id == company_id,
            Order.order_type == "PURCHASE",
            Order.order_date == today,
            Order.status != "CANCELLED",
        )
        .scalar() or 0.0
    )
    pending_orders = (
        db.query(func.count(Order.id))
        .filter(Order.company_id == company_id, Order.status.in_(["DRAFT", "CONFIRMED"]))
        .scalar() or 0
    )
    low_stock_items = (
        db.query(func.count(StockItem.id))
        .filter(StockItem.company_id == company_id, StockItem.is_low_stock == True)
        .scalar() or 0
    )
    total_inventory_value = (
        db.query(func.coalesce(func.sum(StockItem.closing_value), 0.0))
        .filter(StockItem.company_id == company_id)
        .scalar() or 0.0
    )
    company = db.query(Company).filter(Company.id == company_id).first()

    return DashboardKPI(
        total_orders_today=orders_today,
        total_sales_today=round(sales_today, 2),
        total_purchase_today=round(purchase_today, 2),
        pending_orders=pending_orders,
        low_stock_items=low_stock_items,
        total_inventory_value=round(total_inventory_value, 2),
        recent_synced_at=company.last_synced_at if company else None,
    )


# ─── Sales Report ─────────────────────────────────────────────────────────────

@router.get("/sales")
def sales_report(
    company_id: int = Query(...),
    from_date: Optional[date] = Query(None),
    to_date:   Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    if not from_date:
        from_date = date.today() - timedelta(days=29)
    if not to_date:
        to_date = date.today()

    rows = (
        db.query(
            Order.order_date.label("date"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0.0).label("total_amount"),
        )
        .filter(
            Order.company_id == company_id,
            Order.order_type == "SALES",
            Order.status != "CANCELLED",
            Order.order_date >= from_date,
            Order.order_date <= to_date,
        )
        .group_by(Order.order_date)
        .order_by(Order.order_date)
        .all()
    )
    return [
        {"date": str(r.date), "order_count": r.order_count, "total_amount": round(r.total_amount, 2)}
        for r in rows
    ]


# ─── Purchase Report ──────────────────────────────────────────────────────────

@router.get("/purchases")
def purchase_report(
    company_id: int = Query(...),
    from_date: Optional[date] = Query(None),
    to_date:   Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    if not from_date:
        from_date = date.today() - timedelta(days=29)
    if not to_date:
        to_date = date.today()

    rows = (
        db.query(
            Order.order_date.label("date"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0.0).label("total_amount"),
        )
        .filter(
            Order.company_id == company_id,
            Order.order_type == "PURCHASE",
            Order.status != "CANCELLED",
            Order.order_date >= from_date,
            Order.order_date <= to_date,
        )
        .group_by(Order.order_date)
        .order_by(Order.order_date)
        .all()
    )
    return [
        {"date": str(r.date), "order_count": r.order_count, "total_amount": round(r.total_amount, 2)}
        for r in rows
    ]


# ─── Stock Summary ────────────────────────────────────────────────────────────

@router.get("/stock-summary")
def stock_summary(company_id: int = Query(...), db: Session = Depends(get_db)):
    rows = (
        db.query(
            StockItem.group_name.label("group"),
            func.count(StockItem.id).label("item_count"),
            func.coalesce(func.sum(StockItem.closing_value), 0.0).label("total_value"),
        )
        .filter(StockItem.company_id == company_id)
        .group_by(StockItem.group_name)
        .order_by(func.sum(StockItem.closing_value).desc())
        .all()
    )
    return [
        {"group": r.group or "Uncategorised", "item_count": r.item_count, "total_value": round(r.total_value, 2)}
        for r in rows
    ]


# ─── Low Stock ───────────────────────────────────────────────────────────────

@router.get("/low-stock")
def low_stock_report(company_id: int = Query(...), db: Session = Depends(get_db)):
    items = (
        db.query(StockItem)
        .filter(StockItem.company_id == company_id, StockItem.is_low_stock == True)
        .order_by(StockItem.closing_qty)
        .all()
    )
    return [
        {
            "id": i.id,
            "name": i.tally_name,
            "group": i.group_name,
            "uom": i.uom,
            "closing_qty": i.closing_qty,
            "reorder_level": i.reorder_level,
            "deficit": round(i.reorder_level - i.closing_qty, 4),
        }
        for i in items
    ]


# ─── Party Outstanding ────────────────────────────────────────────────────────

@router.get("/party-outstanding", response_model=List[PartyOutstanding])
def party_outstanding(
    company_id:  int           = Query(...),
    ledger_type: Optional[str] = Query(None, pattern="^(CUSTOMER|SUPPLIER)$"),
    db: Session = Depends(get_db),
):
    q = db.query(Ledger).filter(
        Ledger.company_id == company_id,
        Ledger.closing_balance != 0,
        Ledger.ledger_type.in_(["CUSTOMER", "SUPPLIER"]),
    )
    if ledger_type:
        q = q.filter(Ledger.ledger_type == ledger_type)

    rows = q.order_by(func.abs(Ledger.closing_balance).desc()).all()
    return [
        PartyOutstanding(
            party_name=r.tally_name,
            ledger_type=r.ledger_type,
            closing_balance=round(r.closing_balance, 2),
        )
        for r in rows
    ]


# ─── Fast/Slow Moving Items ───────────────────────────────────────────────────

@router.get("/item-movement")
def item_movement(
    company_id: int = Query(...),
    days:       int = Query(30, ge=1, le=365),
    limit:      int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from_date = date.today() - timedelta(days=days)

    rows = (
        db.query(
            OrderItem.stock_item_name,
            func.count(OrderItem.id).label("order_count"),
            func.coalesce(func.sum(OrderItem.quantity), 0.0).label("total_qty"),
            func.coalesce(func.sum(OrderItem.amount), 0.0).label("total_amount"),
        )
        .join(Order)
        .filter(
            Order.company_id == company_id,
            Order.status != "CANCELLED",
            Order.order_date >= from_date,
        )
        .group_by(OrderItem.stock_item_name)
        .order_by(func.sum(OrderItem.amount).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "name": r.stock_item_name,
            "order_count": r.order_count,
            "total_qty": round(r.total_qty, 4),
            "total_amount": round(r.total_amount, 2),
        }
        for r in rows
    ]


# ─── Party-wise Sales ─────────────────────────────────────────────────────────

@router.get("/party-sales")
def party_sales(
    company_id: int = Query(...),
    from_date: Optional[date] = Query(None),
    to_date:   Optional[date] = Query(None),
    limit:     int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if not from_date:
        from_date = date.today() - timedelta(days=29)
    if not to_date:
        to_date = date.today()

    rows = (
        db.query(
            Order.party_name,
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0.0).label("total_amount"),
        )
        .filter(
            Order.company_id == company_id,
            Order.order_type == "SALES",
            Order.status != "CANCELLED",
            Order.order_date >= from_date,
            Order.order_date <= to_date,
        )
        .group_by(Order.party_name)
        .order_by(func.sum(Order.total_amount).desc())
        .limit(limit)
        .all()
    )
    return [
        {"party": r.party_name, "order_count": r.order_count, "total_amount": round(r.total_amount, 2)}
        for r in rows
    ]
