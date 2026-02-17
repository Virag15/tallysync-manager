"""
TallySync Manager — SQLAlchemy ORM Models
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float,
    ForeignKey, Integer, String, Text, func,
)
from sqlalchemy.orm import relationship

from database import Base


# ─── Company (Tally host config) ─────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id                    = Column(Integer, primary_key=True, index=True)
    name                  = Column(String(200), nullable=False)          # display label
    tally_company_name    = Column(String(200), nullable=False)          # exact name in Tally
    host                  = Column(String(100), nullable=False, default="localhost")
    port                  = Column(Integer, nullable=False, default=9000)
    is_active             = Column(Boolean, default=True, nullable=False)
    sync_interval_minutes = Column(Integer, default=5, nullable=False)
    last_synced_at        = Column(DateTime, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    stock_items = relationship("StockItem", back_populates="company", cascade="all, delete-orphan")
    ledgers     = relationship("Ledger",    back_populates="company", cascade="all, delete-orphan")
    orders      = relationship("Order",     back_populates="company")
    vouchers    = relationship("VoucherCache", back_populates="company", cascade="all, delete-orphan")
    sync_logs   = relationship("SyncLog",   back_populates="company", cascade="all, delete-orphan")


# ─── StockItem (cached from Tally) ───────────────────────────────────────────

class StockItem(Base):
    __tablename__ = "stock_items"

    id             = Column(Integer, primary_key=True, index=True)
    company_id     = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tally_name     = Column(String(300), nullable=False)
    alias          = Column(String(300), nullable=True)
    group_name     = Column(String(200), nullable=True)
    uom            = Column(String(50),  nullable=True)
    closing_qty    = Column(Float, default=0.0)
    closing_value  = Column(Float, default=0.0)
    rate           = Column(Float, default=0.0)           # closing value / qty
    reorder_level  = Column(Float, default=0.0)
    is_low_stock   = Column(Boolean, default=False)
    last_synced_at = Column(DateTime, nullable=True)

    company     = relationship("Company", back_populates="stock_items")
    order_items = relationship("OrderItem", back_populates="stock_item")


# ─── Ledger (parties from Tally) ─────────────────────────────────────────────

class Ledger(Base):
    __tablename__ = "ledgers"

    id              = Column(Integer, primary_key=True, index=True)
    company_id      = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    tally_name      = Column(String(300), nullable=False)
    alias           = Column(String(300), nullable=True)
    group_name      = Column(String(200), nullable=True)
    ledger_type     = Column(String(20), nullable=True)   # CUSTOMER | SUPPLIER | OTHER
    opening_balance = Column(Float, default=0.0)
    closing_balance = Column(Float, default=0.0)
    last_synced_at  = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="ledgers")
    orders  = relationship("Order", back_populates="party_ledger")


# ─── Order ───────────────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id                    = Column(Integer, primary_key=True, index=True)
    company_id            = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    order_number          = Column(String(100), nullable=False)
    order_type            = Column(String(20), nullable=False)  # SALES | PURCHASE
    order_date            = Column(Date, nullable=False)
    party_name            = Column(String(300), nullable=False)
    party_ledger_id       = Column(Integer, ForeignKey("ledgers.id"), nullable=True)
    status                = Column(String(20), default="DRAFT")  # DRAFT | CONFIRMED | PUSHED | CANCELLED
    tally_voucher_number  = Column(String(100), nullable=True)
    narration             = Column(Text, nullable=True)
    total_amount          = Column(Float, default=0.0)
    pushed_at             = Column(DateTime, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company      = relationship("Company", back_populates="orders")
    party_ledger = relationship("Ledger", back_populates="orders")
    items        = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


# ─── OrderItem ───────────────────────────────────────────────────────────────

class OrderItem(Base):
    __tablename__ = "order_items"

    id              = Column(Integer, primary_key=True, index=True)
    order_id        = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_item_name = Column(String(300), nullable=False)
    stock_item_id   = Column(Integer, ForeignKey("stock_items.id"), nullable=True)
    quantity        = Column(Float, nullable=False)
    rate            = Column(Float, nullable=False)
    uom             = Column(String(50), nullable=True)
    amount          = Column(Float, nullable=False)  # quantity * rate

    order      = relationship("Order", back_populates="items")
    stock_item = relationship("StockItem", back_populates="order_items")


# ─── VoucherCache (synced from Tally) ────────────────────────────────────────

class VoucherCache(Base):
    __tablename__ = "voucher_cache"

    id             = Column(Integer, primary_key=True, index=True)
    company_id     = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    voucher_number = Column(String(100), nullable=True)
    voucher_type   = Column(String(100), nullable=False)  # Sales Order, Purchase Order, Sales, Purchase, etc.
    voucher_date   = Column(Date, nullable=True)
    party_name     = Column(String(300), nullable=True)
    narration      = Column(Text, nullable=True)
    amount         = Column(Float, default=0.0)
    last_synced_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="vouchers")


# ─── SyncLog ─────────────────────────────────────────────────────────────────

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id              = Column(Integer, primary_key=True, index=True)
    company_id      = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    sync_type       = Column(String(50), nullable=False)   # STOCK | LEDGER | VOUCHER | FULL
    status          = Column(String(20), nullable=False)   # SUCCESS | FAILED | PARTIAL
    records_synced  = Column(Integer, default=0)
    error_message   = Column(Text, nullable=True)
    started_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at    = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    company = relationship("Company", back_populates="sync_logs")
