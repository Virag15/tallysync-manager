"""
TallySync Manager — Orders Routes
Create, manage, and push orders to Tally Prime.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.db_models import Company, Order, OrderItem, StockItem
from models.schemas import (
    OrderCreate, OrderUpdate, OrderResponse, PushResult
)
from sync import sync_company
from tally_client import TallyClient
from tally.xml_builder import OrderLineData

logger = logging.getLogger("tallysync.routes.orders")
router = APIRouter(prefix="/api/orders", tags=["orders"])

# Order number prefix per type
_PREFIX = {"SALES": "SO", "PURCHASE": "PO"}


def _generate_order_number(db: Session, company_id: int, order_type: str) -> str:
    prefix = _PREFIX.get(order_type, "ORD")
    count = (
        db.query(func.count(Order.id))
        .filter(Order.company_id == company_id, Order.order_type == order_type)
        .scalar()
        or 0
    )
    return f"{prefix}-{date.today().strftime('%Y%m')}-{count + 1:04d}"


# ─── List ─────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[OrderResponse])
def list_orders(
    company_id:  int           = Query(...),
    order_type:  Optional[str] = Query(None, pattern="^(SALES|PURCHASE)$"),
    status:      Optional[str] = Query(None),
    from_date:   Optional[date] = Query(None),
    to_date:     Optional[date] = Query(None),
    party_name:  Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.company_id == company_id)
    )
    if order_type:
        q = q.filter(Order.order_type == order_type)
    if status:
        q = q.filter(Order.status == status)
    if from_date:
        q = q.filter(Order.order_date >= from_date)
    if to_date:
        q = q.filter(Order.order_date <= to_date)
    if party_name:
        q = q.filter(Order.party_name.ilike(f"%{party_name}%"))

    return q.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()


# ─── Get by ID ───────────────────────────────────────────────────────────────

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ─── Create ──────────────────────────────────────────────────────────────────

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    order_number = _generate_order_number(db, payload.company_id, payload.order_type)

    # Build items + calculate total
    items = []
    total = 0.0
    for item_data in payload.items:
        amount = round(item_data.quantity * item_data.rate, 2)
        total += amount
        # Try to resolve stock_item_id if not provided
        stock_item_id = item_data.stock_item_id
        if not stock_item_id:
            si = db.query(StockItem).filter(
                StockItem.company_id == payload.company_id,
                StockItem.tally_name == item_data.stock_item_name,
            ).first()
            stock_item_id = si.id if si else None

        items.append(OrderItem(
            stock_item_name=item_data.stock_item_name,
            stock_item_id=stock_item_id,
            quantity=item_data.quantity,
            rate=item_data.rate,
            uom=item_data.uom,
            amount=amount,
        ))

    order = Order(
        company_id=payload.company_id,
        order_number=order_number,
        order_type=payload.order_type,
        order_date=payload.order_date,
        party_name=payload.party_name,
        party_ledger_id=payload.party_ledger_id,
        narration=payload.narration,
        total_amount=round(total, 2),
        items=items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    logger.info("Created order '%s' (id=%d)", order_number, order.id)
    return order


# ─── Update ──────────────────────────────────────────────────────────────────

@router.put("/{order_id}", response_model=OrderResponse)
def update_order(order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "PUSHED":
        raise HTTPException(status_code=400, detail="Cannot edit an order that has been pushed to Tally")

    update_data = payload.model_dump(exclude_none=True)
    items_data = update_data.pop("items", None)

    for field, value in update_data.items():
        setattr(order, field, value)

    if items_data is not None:
        # Replace all items
        for item in order.items:
            db.delete(item)
        total = 0.0
        new_items = []
        for item_data in items_data:
            amount = round(item_data.quantity * item_data.rate, 2)
            total += amount
            new_items.append(OrderItem(
                order_id=order.id,
                stock_item_name=item_data.stock_item_name,
                stock_item_id=item_data.stock_item_id,
                quantity=item_data.quantity,
                rate=item_data.rate,
                uom=item_data.uom,
                amount=amount,
            ))
        order.items = new_items
        order.total_amount = round(total, 2)

    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order


# ─── Delete ──────────────────────────────────────────────────────────────────

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status not in ("DRAFT", "CANCELLED"):
        raise HTTPException(status_code=400, detail="Only DRAFT or CANCELLED orders can be deleted")
    db.delete(order)
    db.commit()


# ─── Push to Tally ───────────────────────────────────────────────────────────

@router.post("/{order_id}/push", response_model=PushResult)
async def push_order_to_tally(order_id: int, db: Session = Depends(get_db)):
    order = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.company))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "PUSHED":
        raise HTTPException(status_code=400, detail="Order already pushed to Tally")
    if order.status not in ("DRAFT", "CONFIRMED"):
        raise HTTPException(status_code=400, detail=f"Cannot push order with status '{order.status}'")
    if not order.items:
        raise HTTPException(status_code=400, detail="Order has no items")

    company = order.company
    client = TallyClient(company.host, company.port)

    lines = [
        OrderLineData(
            stock_item_name=item.stock_item_name,
            quantity=item.quantity,
            rate=item.rate,
            amount=item.amount,
            uom=item.uom or "Nos",
            is_sales=order.order_type == "SALES",
        )
        for item in order.items
    ]

    if order.order_type == "SALES":
        success, message, voucher_number = await client.push_sales_order(
            company.tally_company_name,
            order.order_number,
            order.order_date,
            order.party_name,
            lines,
            order.narration or "",
        )
    else:
        success, message, voucher_number = await client.push_purchase_order(
            company.tally_company_name,
            order.order_number,
            order.order_date,
            order.party_name,
            lines,
            order.narration or "",
        )

    if success:
        order.status = "PUSHED"
        order.pushed_at = datetime.utcnow()
        order.tally_voucher_number = voucher_number
        db.commit()

    return PushResult(success=success, message=message, tally_voucher_number=voucher_number)
