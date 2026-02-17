"""
TallySync Manager — Tally Prime XML Response Parser
Converts Tally's XML responses into clean Python dicts.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import xmltodict

# Characters invalid in XML 1.0 (Tally sometimes includes raw control chars)
_INVALID_XML_CHARS = re.compile(
    r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)

# Numeric character entity references (&#NNN; or &#xHH;) pointing to invalid codepoints.
# Tally sometimes emits e.g. &#8; (backspace) or &#x1C; (file separator) in item names.
_CHAR_REF = re.compile(r"&#(?:([0-9]+)|x([0-9A-Fa-f]+));")

def _is_valid_xml_cp(cp: int) -> bool:
    """True if codepoint is legal in XML 1.0."""
    return (cp in (0x09, 0x0A, 0x0D)
            or 0x20 <= cp <= 0xD7FF
            or 0xE000 <= cp <= 0xFFFD
            or 0x10000 <= cp <= 0x10FFFF)

def _strip_invalid_char_refs(text: str) -> str:
    """Remove &#NN; / &#xHH; entity refs that reference invalid XML 1.0 codepoints."""
    def _sub(m: re.Match) -> str:
        dec, hex_ = m.group(1), m.group(2)
        cp = int(dec) if dec is not None else int(hex_, 16)
        return m.group(0) if _is_valid_xml_cp(cp) else ""
    return _CHAR_REF.sub(_sub, text)

logger = logging.getLogger("tallysync.xml_parser")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Parse Tally numeric strings (may contain spaces, minus signs)."""
    if value is None:
        return default
    try:
        return float(str(value).replace(" ", "").replace(",", ""))
    except (ValueError, TypeError):
        return default


def _safe_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def _tally_date_to_python(tally_date: Any) -> Optional[date]:
    """Convert Tally date string YYYYMMDD → Python date."""
    raw = _safe_str(tally_date)
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y%m%d").date()
    except ValueError:
        return None


def _ensure_list(value: Any) -> List[Any]:
    """Tally returns a single dict instead of list when there's only one item."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_xml(xml_text: str) -> Dict:
    try:
        # 1. Strip raw bytes that are illegal in XML 1.0 (e.g. 0x01-0x08, 0x0B…)
        clean = _INVALID_XML_CHARS.sub("", xml_text)
        # 2. Remove numeric char-refs pointing to invalid codepoints (e.g. &#8; &#x1C;)
        clean = _strip_invalid_char_refs(clean)
        return xmltodict.parse(clean, force_list=False)
    except Exception as exc:
        logger.error("XML parse error: %s | raw: %.200s", exc, xml_text)
        return {}


# ─── Parsers ─────────────────────────────────────────────────────────────────

def parse_companies(xml_text: str) -> List[str]:
    """Extract company names from Tally's company list response."""
    data = _parse_xml(xml_text)
    companies: List[str] = []
    try:
        envelope = data.get("ENVELOPE", {})
        body = envelope.get("BODY", {})
        companies_data = body.get("DATA", {}).get("COLLECTION", {}).get("COMPANY", [])
        for co in _ensure_list(companies_data):
            name = _safe_str(co.get("NAME") or co.get("@NAME"))
            if name:
                companies.append(name)
    except Exception as exc:
        logger.warning("parse_companies error: %s", exc)
    return companies


def parse_tally_version(xml_text: str) -> Optional[str]:
    """Extract Tally version from license/company info response."""
    data = _parse_xml(xml_text)
    try:
        return _safe_str(
            data.get("ENVELOPE", {})
                .get("HEADER", {})
                .get("VERSION")
        )
    except Exception:
        return None


def parse_stock_items(xml_text: str) -> List[Dict]:
    """
    Parse Stock Summary response into list of stock item dicts.
    Returns: [{name, group, uom, closing_qty, closing_value, rate}, ...]
    """
    data = _parse_xml(xml_text)
    items: List[Dict] = []
    try:
        envelope = data.get("ENVELOPE", {})
        body = envelope.get("BODY", {}) or envelope.get("BODY", {})
        # Stock Summary has DSPACCSUM collection
        collection = (
            body.get("DATA", {})
                .get("COLLECTION", {})
        )
        raw_items = (
            collection.get("STOCKITEM", [])
            or collection.get("DSPACCSUM", [])
            or []
        )
        for item in _ensure_list(raw_items):
            name = _safe_str(item.get("NAME") or item.get("STOCKITEMNAME"))
            if not name:
                continue
            closing_qty   = _safe_float(item.get("CLOSINGBALANCE") or item.get("DSPCLQTY"))
            closing_value = _safe_float(item.get("CLOSINGVALUE") or item.get("DSPCLVAL"))
            rate = (closing_value / closing_qty) if closing_qty and closing_qty != 0 else 0.0
            items.append({
                "tally_name":    name,
                "alias":         _safe_str(item.get("ALIAS")),
                "group_name":    _safe_str(item.get("PARENT") or item.get("DSPSTOCKGROUP")),
                "uom":           _safe_str(item.get("BASEUNITS") or item.get("DSPUOM")),
                "closing_qty":   round(closing_qty, 4),
                "closing_value": round(closing_value, 2),
                "rate":          round(rate, 4),
            })
    except Exception as exc:
        logger.error("parse_stock_items error: %s", exc)
    return items


def parse_ledgers(xml_text: str) -> List[Dict]:
    """
    Parse List of Accounts (Ledger) response.
    Returns: [{name, alias, group, ledger_type, opening_balance, closing_balance}, ...]
    """
    data = _parse_xml(xml_text)
    ledgers: List[Dict] = []
    CUSTOMER_GROUPS = {"sundry debtors"}
    SUPPLIER_GROUPS = {"sundry creditors"}

    try:
        raw_ledgers = (
            data.get("ENVELOPE", {})
                .get("BODY", {})
                .get("DATA", {})
                .get("COLLECTION", {})
                .get("LEDGER", [])
        )
        for ledger in _ensure_list(raw_ledgers):
            name  = _safe_str(ledger.get("NAME"))
            group = _safe_str(ledger.get("PARENT") or ledger.get("LEDGERGROUPNAME")) or ""
            if not name:
                continue
            group_lower = group.lower()
            if group_lower in CUSTOMER_GROUPS:
                ledger_type = "CUSTOMER"
            elif group_lower in SUPPLIER_GROUPS:
                ledger_type = "SUPPLIER"
            else:
                ledger_type = "OTHER"

            closing = _safe_float(ledger.get("CLOSINGBALANCE"))
            opening = _safe_float(ledger.get("OPENINGBALANCE"))
            ledgers.append({
                "tally_name":      name,
                "alias":           _safe_str(ledger.get("ALIAS")),
                "group_name":      group or None,
                "ledger_type":     ledger_type,
                "opening_balance": round(opening, 2),
                "closing_balance": round(closing, 2),
            })
    except Exception as exc:
        logger.error("parse_ledgers error: %s", exc)
    return ledgers


def parse_vouchers(xml_text: str) -> List[Dict]:
    """
    Parse Voucher Register response.
    Returns: [{voucher_number, voucher_type, voucher_date, party_name, amount, narration}, ...]
    """
    data = _parse_xml(xml_text)
    vouchers: List[Dict] = []
    try:
        raw = (
            data.get("ENVELOPE", {})
                .get("BODY", {})
                .get("DATA", {})
                .get("COLLECTION", {})
                .get("VOUCHER", [])
        )
        for v in _ensure_list(raw):
            vouchers.append({
                "voucher_number": _safe_str(v.get("VOUCHERNUMBER")),
                "voucher_type":   _safe_str(v.get("VOUCHERTYPENAME")),
                "voucher_date":   _tally_date_to_python(v.get("DATE")),
                "party_name":     _safe_str(v.get("PARTYLEDGERNAME")),
                "narration":      _safe_str(v.get("NARRATION")),
                "amount":         abs(_safe_float(v.get("AMOUNT"))),
            })
    except Exception as exc:
        logger.error("parse_vouchers error: %s", exc)
    return vouchers


def parse_import_response(xml_text: str) -> tuple[bool, str, Optional[str]]:
    """
    Parse Tally's response to an Import Data request.
    Returns: (success: bool, message: str, voucher_number: Optional[str])

    Tally Prime returns one of two structures:
      A) <ENVELOPE><BODY><IMPORTRESULT><CREATED>1</CREATED>...</IMPORTRESULT></BODY></ENVELOPE>
      B) <RESPONSE><CREATED>1</CREATED>...</RESPONSE>   (older Tally)
    Errors appear in <LASTSTMTERROR> or <LINEERROR>.
    """
    data = _parse_xml(xml_text)
    if not data:
        logger.error("parse_import_response: empty/unparseable XML. Raw: %.500s", xml_text)
        return False, "Could not parse Tally response. Check server logs.", None

    try:
        # ── Path A: Tally Prime 3.x — ENVELOPE > BODY > IMPORTRESULT ──────────
        body = data.get("ENVELOPE", {}).get("BODY", {})
        import_result = body.get("IMPORTRESULT") or body.get("DATA", {}).get("IMPORTRESULT")
        if import_result:
            created = _safe_float(import_result.get("CREATED", 0))
            errors  = _safe_float(import_result.get("ERRORS", 0))
            if created > 0:
                return True, f"{int(created)} voucher(s) created in Tally", None
            err_msg = (
                _safe_str(import_result.get("LASTSTMTERROR"))
                or _safe_str(import_result.get("LINEERROR"))
            )
            if err_msg:
                logger.warning("Tally push error: %s", err_msg)
                return False, err_msg, None
            if errors > 0:
                logger.error("Tally returned %d error(s), raw: %.500s", int(errors), xml_text)
                return False, f"Tally rejected the voucher ({int(errors)} error(s)). Check Tally logs.", None

        # ── Path B: older <RESPONSE> wrapper ───────────────────────────────────
        response = data.get("RESPONSE", {})
        if response:
            err_msg = _safe_str(response.get("LINEERROR")) or _safe_str(response.get("LASTSTMTERROR"))
            if err_msg:
                logger.warning("Tally push error: %s", err_msg)
                return False, err_msg, None
            created = _safe_float(response.get("CREATED", 0))
            if created > 0:
                return True, f"{int(created)} voucher(s) created in Tally", None

        # ── Fallback: log full raw response so admin can diagnose ───────────────
        logger.error("parse_import_response: unexpected structure. Raw: %.500s", xml_text)
        return False, "Tally did not confirm the voucher. Check server logs (data/logs/app.log).", None

    except Exception as exc:
        logger.error("parse_import_response error: %s | raw: %.500s", exc, xml_text)
        return False, f"Parse error: {exc}", None
