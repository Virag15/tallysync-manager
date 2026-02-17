"""
TallySync Manager — Tally Prime XML Request Builder
Builds properly formatted XML envelopes for Tally's HTTP API (port 9000).
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _tally_date(d: date) -> str:
    """Convert Python date → Tally date format (YYYYMMDD)."""
    return d.strftime("%Y%m%d")


def _export_envelope(report_name: str, company_name: str, extra_vars: str = "") -> str:
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>{report_name}</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
          <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
          {extra_vars}
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def _import_envelope(company_name: str, message_body: str) -> str:
    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        <STATICVARIABLES>
          <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
        </STATICVARIABLES>
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          {message_body}
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""


# ─── Export Requests ─────────────────────────────────────────────────────────

def build_get_companies() -> str:
    """Fetch all open companies in Tally."""
    return """<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>List of Companies</REPORTNAME>
        <STATICVARIABLES>
          <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>"""


def build_get_stock_items(company_name: str) -> str:
    """Fetch all stock items with closing balance from Tally."""
    return _export_envelope(
        "Stock Summary",
        company_name,
        "<SVFROMDATE>$$BegnOf:Year</SVFROMDATE><SVTODATE>$$DateOf:Today</SVTODATE>",
    )


def build_get_ledgers(company_name: str) -> str:
    """Fetch all ledgers (parties) from Tally."""
    return _export_envelope("List of Accounts", company_name, "<ACCOUNTTYPE>Ledger</ACCOUNTTYPE>")


def build_get_vouchers(
    company_name: str,
    voucher_type: str,
    from_date: date,
    to_date: date,
) -> str:
    """Fetch vouchers of a given type within a date range."""
    return _export_envelope(
        "Voucher Register",
        company_name,
        f"""<SVFROMDATE>{_tally_date(from_date)}</SVFROMDATE>
          <SVTODATE>{_tally_date(to_date)}</SVTODATE>
          <SVVOUCHERTYPE>{voucher_type}</SVVOUCHERTYPE>""",
    )


# ─── Import Requests (push to Tally) ─────────────────────────────────────────

class OrderLineData:
    """Represents one line in a Tally voucher inventory entry."""
    def __init__(
        self,
        stock_item_name: str,
        quantity: float,
        rate: float,
        amount: float,
        uom: str = "Nos",
        is_sales: bool = True,
    ):
        self.stock_item_name = stock_item_name
        self.quantity = quantity
        self.rate = rate
        self.amount = amount
        self.uom = uom
        # Sales = party is debit (positive), inventory credit (negative for amount)
        self.is_deemed_positive = "No" if is_sales else "Yes"


def build_push_sales_order(
    company_name: str,
    order_number: str,
    order_date: date,
    party_name: str,
    lines: List[OrderLineData],
    narration: str = "",
) -> str:
    total = sum(l.amount for l in lines)
    inventory_xml = ""
    for line in lines:
        inventory_xml += f"""
          <INVENTORYENTRIES.LIST>
            <STOCKITEMNAME>{line.stock_item_name}</STOCKITEMNAME>
            <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
            <RATE>{line.rate:.4f}/{line.uom}</RATE>
            <AMOUNT>-{abs(line.amount):.2f}</AMOUNT>
            <ACTUALQTY>{line.quantity:.4f} {line.uom}</ACTUALQTY>
            <BILLEDQTY>{line.quantity:.4f} {line.uom}</BILLEDQTY>
          </INVENTORYENTRIES.LIST>"""

    voucher_xml = f"""<VOUCHER VCHTYPE="Sales Order" ACTION="Create" OBJVIEW="Order Voucher View">
            <DATE>{_tally_date(order_date)}</DATE>
            <EFFECTIVEDATE>{_tally_date(order_date)}</EFFECTIVEDATE>
            <VOUCHERTYPENAME>Sales Order</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{order_number}</VOUCHERNUMBER>
            <PARTYLEDGERNAME>{party_name}</PARTYLEDGERNAME>
            <NARRATION>{narration}</NARRATION>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{party_name}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>{total:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            {inventory_xml}
          </VOUCHER>"""

    return _import_envelope(company_name, voucher_xml)


def build_push_purchase_order(
    company_name: str,
    order_number: str,
    order_date: date,
    party_name: str,
    lines: List[OrderLineData],
    narration: str = "",
) -> str:
    total = sum(l.amount for l in lines)
    inventory_xml = ""
    for line in lines:
        inventory_xml += f"""
          <INVENTORYENTRIES.LIST>
            <STOCKITEMNAME>{line.stock_item_name}</STOCKITEMNAME>
            <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
            <RATE>{line.rate:.4f}/{line.uom}</RATE>
            <AMOUNT>{abs(line.amount):.2f}</AMOUNT>
            <ACTUALQTY>{line.quantity:.4f} {line.uom}</ACTUALQTY>
            <BILLEDQTY>{line.quantity:.4f} {line.uom}</BILLEDQTY>
          </INVENTORYENTRIES.LIST>"""

    voucher_xml = f"""<VOUCHER VCHTYPE="Purchase Order" ACTION="Create" OBJVIEW="Order Voucher View">
            <DATE>{_tally_date(order_date)}</DATE>
            <EFFECTIVEDATE>{_tally_date(order_date)}</EFFECTIVEDATE>
            <VOUCHERTYPENAME>Purchase Order</VOUCHERTYPENAME>
            <VOUCHERNUMBER>{order_number}</VOUCHERNUMBER>
            <PARTYLEDGERNAME>{party_name}</PARTYLEDGERNAME>
            <NARRATION>{narration}</NARRATION>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{party_name}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>-{abs(total):.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            {inventory_xml}
          </VOUCHER>"""

    return _import_envelope(company_name, voucher_xml)
