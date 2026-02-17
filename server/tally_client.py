"""
TallySync Manager — Tally Prime HTTP Client
Sends XML requests to Tally's HTTP server and returns parsed results.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple

import httpx

from tally.xml_builder import (
    build_get_companies,
    build_get_stock_items,
    build_get_ledgers,
    build_get_vouchers,
    build_push_sales_order,
    build_push_purchase_order,
    OrderLineData,
)
from tally.xml_parser import (
    parse_companies,
    parse_tally_version,
    parse_stock_items,
    parse_ledgers,
    parse_vouchers,
    parse_import_response,
)

logger = logging.getLogger("tallysync.tally_client")

CONNECT_TIMEOUT = 10.0    # seconds
READ_TIMEOUT    = 300.0   # Tally can be very slow on large voucher sets (5 min)


class TallyClient:
    """Async HTTP client for a single Tally Prime instance (host:port)."""

    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}"

    async def _post(self, xml: str) -> str:
        """Send XML to Tally and return raw response text."""
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=CONNECT_TIMEOUT, read=READ_TIMEOUT, write=30, pool=5),
        ) as client:
            headers = {"Content-Type": "text/xml; charset=utf-8"}
            response = await client.post(self.base_url, content=xml.encode("utf-8"), headers=headers)
            response.raise_for_status()
            return response.text

    # ─── Connection Test ─────────────────────────────────────────────────────

    async def test_connection(self) -> Tuple[bool, str, List[str]]:
        """
        Test connectivity to Tally.
        Returns (success, message, list_of_open_companies).
        """
        try:
            xml = build_get_companies()
            raw = await self._post(xml)
            companies = parse_companies(raw)
            version   = parse_tally_version(raw)
            return True, f"Connected to Tally{' v' + version if version else ''}", companies
        except httpx.ConnectError:
            return False, f"Cannot connect to Tally at {self.base_url}. Is Tally running with HTTP server enabled?", []
        except httpx.TimeoutException:
            return False, f"Connection timed out to {self.base_url}", []
        except Exception as exc:
            logger.exception("test_connection failed")
            return False, str(exc), []

    # ─── Fetch Methods ───────────────────────────────────────────────────────

    async def fetch_stock_items(self, company_name: str) -> List[Dict]:
        """Pull all stock items with closing balances from Tally."""
        try:
            xml = build_get_stock_items(company_name)
            raw = await self._post(xml)
            items = parse_stock_items(raw)
            logger.info("Fetched %d stock items from '%s'", len(items), company_name)
            return items
        except Exception as exc:
            logger.error("fetch_stock_items failed for '%s': %r", company_name, exc)
            raise

    async def fetch_ledgers(self, company_name: str) -> List[Dict]:
        """Pull all ledgers (parties) from Tally."""
        try:
            xml = build_get_ledgers(company_name)
            raw = await self._post(xml)
            ledgers = parse_ledgers(raw)
            logger.info("Fetched %d ledgers from '%s'", len(ledgers), company_name)
            return ledgers
        except Exception as exc:
            logger.error("fetch_ledgers failed for '%s': %r", company_name, exc)
            raise

    async def fetch_vouchers(
        self,
        company_name: str,
        voucher_type: str = "Sales Order",
        days_back: int = 30,
    ) -> List[Dict]:
        """Pull vouchers of a given type for the last N days."""
        try:
            to_date   = date.today()
            from_date = to_date - timedelta(days=days_back)
            xml = build_get_vouchers(company_name, voucher_type, from_date, to_date)
            raw = await self._post(xml)
            vouchers = parse_vouchers(raw)
            logger.info(
                "Fetched %d '%s' vouchers from '%s'",
                len(vouchers), voucher_type, company_name,
            )
            return vouchers
        except Exception as exc:
            logger.error("fetch_vouchers failed for '%s': %r", company_name, exc)
            raise

    # ─── Push Methods ────────────────────────────────────────────────────────

    async def push_sales_order(
        self,
        company_name: str,
        order_number: str,
        order_date: date,
        party_name: str,
        lines: List[OrderLineData],
        narration: str = "",
    ) -> Tuple[bool, str, Optional[str]]:
        """Push a sales order into Tally as a Sales Order voucher."""
        try:
            xml = build_push_sales_order(
                company_name, order_number, order_date, party_name, lines, narration
            )
            raw = await self._post(xml)
            success, message, voucher_number = parse_import_response(raw)
            if success:
                logger.info("Sales Order '%s' pushed to Tally company '%s'", order_number, company_name)
            else:
                logger.warning("Push Sales Order '%s' failed: %s", order_number, message)
            return success, message, voucher_number
        except Exception as exc:
            logger.error("push_sales_order failed: %s", exc)
            return False, str(exc), None

    async def push_purchase_order(
        self,
        company_name: str,
        order_number: str,
        order_date: date,
        party_name: str,
        lines: List[OrderLineData],
        narration: str = "",
    ) -> Tuple[bool, str, Optional[str]]:
        """Push a purchase order into Tally as a Purchase Order voucher."""
        try:
            xml = build_push_purchase_order(
                company_name, order_number, order_date, party_name, lines, narration
            )
            raw = await self._post(xml)
            success, message, voucher_number = parse_import_response(raw)
            if success:
                logger.info("Purchase Order '%s' pushed to Tally company '%s'", order_number, company_name)
            else:
                logger.warning("Push Purchase Order '%s' failed: %s", order_number, message)
            return success, message, voucher_number
        except Exception as exc:
            logger.error("push_purchase_order failed: %s", exc)
            return False, str(exc), None
