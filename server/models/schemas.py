"""
TallySync Manager — Pydantic Schemas (request / response)
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ─── App Info ────────────────────────────────────────────────────────────────

class AppInfo(BaseModel):
    name: str
    version: str
    build: str
    db_path: str


# ─── Company ─────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str                   = Field(..., min_length=1, max_length=200)
    tally_company_name: str     = Field(..., min_length=1, max_length=200)
    host: str                   = Field(default="localhost", max_length=100)
    port: int                   = Field(default=9000, ge=1, le=65535)
    sync_interval_minutes: int  = Field(default=5, ge=1, le=1440)


class CompanyUpdate(BaseModel):
    name: Optional[str]                  = Field(None, min_length=1, max_length=200)
    tally_company_name: Optional[str]    = Field(None, min_length=1, max_length=200)
    host: Optional[str]                  = Field(None, max_length=100)
    port: Optional[int]                  = Field(None, ge=1, le=65535)
    sync_interval_minutes: Optional[int] = Field(None, ge=1, le=1440)
    is_active: Optional[bool]            = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    tally_company_name: str
    host: str
    port: int
    is_active: bool
    sync_interval_minutes: int
    last_synced_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    tally_version: Optional[str] = None
    open_companies: List[str]    = []


# ─── Stock Item ──────────────────────────────────────────────────────────────

class StockItemResponse(BaseModel):
    id: int
    company_id: int
    tally_name: str
    alias: Optional[str]
    group_name: Optional[str]
    uom: Optional[str]
    closing_qty: float
    closing_value: float
    rate: float
    reorder_level: float
    is_low_stock: bool
    last_synced_at: Optional[datetime]

    model_config = {"from_attributes": True}


class StockStats(BaseModel):
    total_items: int
    low_stock_count: int
    total_value: float
    groups: List[str]


# ─── Ledger ──────────────────────────────────────────────────────────────────

class LedgerResponse(BaseModel):
    id: int
    company_id: int
    tally_name: str
    alias: Optional[str]
    group_name: Optional[str]
    ledger_type: Optional[str]
    opening_balance: float
    closing_balance: float

    model_config = {"from_attributes": True}


# ─── Order Item ──────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    stock_item_name: str = Field(..., min_length=1)
    stock_item_id: Optional[int] = None
    quantity: float      = Field(..., gt=0)
    rate: float          = Field(..., gt=0)
    uom: Optional[str]   = None

    @field_validator("quantity", "rate")
    @classmethod
    def must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("must be > 0")
        return round(v, 4)


class OrderItemResponse(BaseModel):
    id: int
    stock_item_name: str
    stock_item_id: Optional[int]
    quantity: float
    rate: float
    uom: Optional[str]
    amount: float

    model_config = {"from_attributes": True}


# ─── Order ───────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    company_id: int
    order_type: str          = Field(..., pattern="^(SALES|PURCHASE)$")
    order_date: date
    party_name: str          = Field(..., min_length=1)
    party_ledger_id: Optional[int] = None
    narration: Optional[str] = None
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderUpdate(BaseModel):
    order_date: Optional[date]       = None
    party_name: Optional[str]        = None
    party_ledger_id: Optional[int]   = None
    narration: Optional[str]         = None
    status: Optional[str]            = Field(None, pattern="^(DRAFT|CONFIRMED|CANCELLED)$")
    items: Optional[List[OrderItemCreate]] = None


class OrderResponse(BaseModel):
    id: int
    company_id: int
    order_number: str
    order_type: str
    order_date: date
    party_name: str
    party_ledger_id: Optional[int]
    status: str
    tally_voucher_number: Optional[str]
    narration: Optional[str]
    total_amount: float
    pushed_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class PushResult(BaseModel):
    success: bool
    message: str
    tally_voucher_number: Optional[str] = None


# ─── Voucher ─────────────────────────────────────────────────────────────────

class VoucherResponse(BaseModel):
    id: int
    company_id: int
    voucher_number: Optional[str]
    voucher_type: str
    voucher_date: Optional[date]
    party_name: Optional[str]
    narration: Optional[str]
    amount: float
    last_synced_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ─── Sync ────────────────────────────────────────────────────────────────────

class SyncStatus(BaseModel):
    company_id: int
    company_name: str
    last_synced_at: Optional[datetime]
    last_sync_status: Optional[str]
    stock_items_count: int
    ledgers_count: int


class SyncLogResponse(BaseModel):
    id: int
    company_id: int
    sync_type: str
    status: str
    records_synced: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]

    model_config = {"from_attributes": True}


# ─── Reports ─────────────────────────────────────────────────────────────────

class DashboardKPI(BaseModel):
    total_orders_today: int
    total_sales_today: float
    total_purchase_today: float
    pending_orders: int
    low_stock_items: int
    total_inventory_value: float
    recent_synced_at: Optional[datetime]


class StockMovementItem(BaseModel):
    stock_item_name: str
    order_type: str
    quantity: float
    amount: float
    order_date: date


class PartyOutstanding(BaseModel):
    party_name: str
    ledger_type: str
    closing_balance: float
