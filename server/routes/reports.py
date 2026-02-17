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
from sqlalchemy import union_all, literal, String

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


# ─── Creditors Aging (AP Aging Report) ───────────────────────────────────────

@router.get("/creditors-aging")
def creditors_aging(
    company_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    Accounts Payable aging report.
    For each supplier with an outstanding balance, breaks down purchase
    transactions into 0-30, 31-60, 61-90, 91-180, and 180+ day buckets.

    Data sources:
      • Ledger.closing_balance  — authoritative total outstanding per creditor
      • Orders (PURCHASE, not CANCELLED) — local orders as invoice proxies
      • VoucherCache (Purchase Order) — vouchers synced from Tally

    The bucket amounts show the *purchase profile* (how much was ordered in
    each age band). The closing_balance from Tally is the ground truth for
    total outstanding.
    """
    today = date.today()

    # ── Step 1: All SUPPLIER ledgers with a balance ───────────────────────────
    suppliers = (
        db.query(Ledger)
        .filter(
            Ledger.company_id == company_id,
            Ledger.ledger_type == "SUPPLIER",
            Ledger.closing_balance != 0,
        )
        .order_by(Ledger.closing_balance.desc())
        .all()
    )
    if not suppliers:
        return []

    supplier_names = {s.tally_name: s for s in suppliers}

    # ── Step 2: Purchase transactions from Orders table ───────────────────────
    local_orders = (
        db.query(
            Order.party_name,
            Order.order_date,
            Order.total_amount,
        )
        .filter(
            Order.company_id == company_id,
            Order.order_type == "PURCHASE",
            Order.status != "CANCELLED",
        )
        .all()
    )

    # ── Step 3: Purchase vouchers from Tally cache ────────────────────────────
    cached_vouchers = (
        db.query(
            VoucherCache.party_name,
            VoucherCache.voucher_date,
            VoucherCache.amount,
        )
        .filter(
            VoucherCache.company_id == company_id,
            VoucherCache.voucher_type == "Purchase Order",
            VoucherCache.party_name.isnot(None),
            VoucherCache.amount > 0,
        )
        .all()
    )

    # ── Step 4: Build per-party transaction list ──────────────────────────────
    from collections import defaultdict
    party_txns: dict = defaultdict(list)

    for o in local_orders:
        if o.party_name:
            party_txns[o.party_name].append((o.order_date, o.total_amount))

    for v in cached_vouchers:
        if v.party_name:
            party_txns[v.party_name].append((v.voucher_date, v.amount))

    # ── Step 5: Compute aging per supplier ────────────────────────────────────
    def _age_days(txn_date) -> int:
        if txn_date is None:
            return 999
        if hasattr(txn_date, 'date'):
            txn_date = txn_date.date()
        return (today - txn_date).days

    results = []
    for supplier in suppliers:
        name = supplier.tally_name
        txns = party_txns.get(name, [])

        b0_30 = b31_60 = b61_90 = b91_180 = b180_plus = 0.0
        oldest_days = 0
        last_txn_date = None
        total_txn_amount = 0.0

        for txn_date, amount in txns:
            age = _age_days(txn_date)
            total_txn_amount += amount
            if age > oldest_days:
                oldest_days = age
            if last_txn_date is None or (txn_date is not None and txn_date > last_txn_date):
                last_txn_date = txn_date

            if age <= 30:
                b0_30 += amount
            elif age <= 60:
                b31_60 += amount
            elif age <= 90:
                b61_90 += amount
            elif age <= 180:
                b91_180 += amount
            else:
                b180_plus += amount

        results.append({
            "party_name":          name,
            "ledger_type":         supplier.ledger_type,
            "total_outstanding":   round(supplier.closing_balance, 2),
            "current_0_30":        round(b0_30, 2),
            "days_31_60":          round(b31_60, 2),
            "days_61_90":          round(b61_90, 2),
            "days_91_180":         round(b91_180, 2),
            "days_180_plus":       round(b180_plus, 2),
            "total_invoiced":      round(total_txn_amount, 2),
            "oldest_invoice_days": oldest_days if txns else None,
            "last_transaction_date": str(last_txn_date) if last_txn_date else None,
            "transaction_count":   len(txns),
        })

    return results
