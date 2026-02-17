#!/usr/bin/env python3
"""
TallySync Manager — Mock Tally Prime Server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Simulates Tally's HTTP XML API on port 9000 so you can test TallySync
on any machine — even one that doesn't have Tally Prime installed.

Usage:
    python mock_tally.py          # port 9000 (default)
    python mock_tally.py 9001     # custom port

What it does:
    - Accepts the same POST requests that Tally's HTTP server accepts
    - Returns realistic sample XML (Indian company, stock items, ledgers)
    - Voucher push (Sales Order / Purchase Order) always succeeds
    - Runs entirely in Python stdlib — no pip install needed
"""

import sys
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000

# ── Mock XML Responses ────────────────────────────────────────────────────────

_COMPANIES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <COMPANY><NAME>Demo Trading Co.</NAME></COMPANY>
        <COMPANY><NAME>Sample Enterprises Pvt Ltd</NAME></COMPANY>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>"""

_STOCK_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <STOCKITEM>
          <NAME>Basmati Rice Premium</NAME>
          <PARENT>Food &amp; Grains</PARENT>
          <BASEUNITS>Kg</BASEUNITS>
          <CLOSINGBALANCE>250.000</CLOSINGBALANCE>
          <CLOSINGVALUE>37500.00</CLOSINGVALUE>
        </STOCKITEM>
        <STOCKITEM>
          <NAME>Sunflower Oil 1L</NAME>
          <PARENT>Edible Oils</PARENT>
          <BASEUNITS>Nos</BASEUNITS>
          <CLOSINGBALANCE>120.000</CLOSINGBALANCE>
          <CLOSINGVALUE>14400.00</CLOSINGVALUE>
        </STOCKITEM>
        <STOCKITEM>
          <NAME>Toor Dal 500g</NAME>
          <PARENT>Pulses</PARENT>
          <BASEUNITS>Pkt</BASEUNITS>
          <CLOSINGBALANCE>300.000</CLOSINGBALANCE>
          <CLOSINGVALUE>21000.00</CLOSINGVALUE>
        </STOCKITEM>
        <STOCKITEM>
          <NAME>Wheat Flour 5Kg</NAME>
          <PARENT>Food &amp; Grains</PARENT>
          <BASEUNITS>Nos</BASEUNITS>
          <CLOSINGBALANCE>85.000</CLOSINGBALANCE>
          <CLOSINGVALUE>16150.00</CLOSINGVALUE>
        </STOCKITEM>
        <STOCKITEM>
          <NAME>Sugar 1Kg</NAME>
          <PARENT>Food &amp; Grains</PARENT>
          <BASEUNITS>Kg</BASEUNITS>
          <CLOSINGBALANCE>200.000</CLOSINGBALANCE>
          <CLOSINGVALUE>9200.00</CLOSINGVALUE>
        </STOCKITEM>
        <STOCKITEM>
          <NAME>Mustard Oil 500ml</NAME>
          <PARENT>Edible Oils</PARENT>
          <BASEUNITS>Nos</BASEUNITS>
          <CLOSINGBALANCE>60.000</CLOSINGBALANCE>
          <CLOSINGVALUE>4200.00</CLOSINGVALUE>
        </STOCKITEM>
        <STOCKITEM>
          <NAME>Chana Dal 1Kg</NAME>
          <PARENT>Pulses</PARENT>
          <BASEUNITS>Kg</BASEUNITS>
          <CLOSINGBALANCE>180.000</CLOSINGBALANCE>
          <CLOSINGVALUE>14400.00</CLOSINGVALUE>
        </STOCKITEM>
        <STOCKITEM>
          <NAME>Ghee 1Kg Tin</NAME>
          <PARENT>Dairy Products</PARENT>
          <BASEUNITS>Nos</BASEUNITS>
          <CLOSINGBALANCE>40.000</CLOSINGBALANCE>
          <CLOSINGVALUE>22000.00</CLOSINGVALUE>
        </STOCKITEM>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>"""

_LEDGERS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <LEDGER>
          <NAME>Raj Traders</NAME>
          <PARENT>Sundry Debtors</PARENT>
          <CLOSINGBALANCE>85000.00</CLOSINGBALANCE>
          <OPENINGBALANCE>30000.00</OPENINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Mehta &amp; Sons</NAME>
          <PARENT>Sundry Debtors</PARENT>
          <CLOSINGBALANCE>42500.00</CLOSINGBALANCE>
          <OPENINGBALANCE>0.00</OPENINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Sharma General Store</NAME>
          <PARENT>Sundry Debtors</PARENT>
          <CLOSINGBALANCE>18200.00</CLOSINGBALANCE>
          <OPENINGBALANCE>5000.00</OPENINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Patel Wholesalers</NAME>
          <PARENT>Sundry Creditors</PARENT>
          <CLOSINGBALANCE>65000.00</CLOSINGBALANCE>
          <OPENINGBALANCE>20000.00</OPENINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Singh Distributors</NAME>
          <PARENT>Sundry Creditors</PARENT>
          <CLOSINGBALANCE>28000.00</CLOSINGBALANCE>
          <OPENINGBALANCE>0.00</OPENINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Cash</NAME>
          <PARENT>Cash-in-Hand</PARENT>
          <CLOSINGBALANCE>15000.00</CLOSINGBALANCE>
          <OPENINGBALANCE>10000.00</OPENINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>HDFC Bank Current A/C</NAME>
          <PARENT>Bank Accounts</PARENT>
          <CLOSINGBALANCE>230000.00</CLOSINGBALANCE>
          <OPENINGBALANCE>150000.00</OPENINGBALANCE>
        </LEDGER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>"""

_SALES_VOUCHERS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <VOUCHER>
          <VOUCHERNUMBER>SO-2026-001</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Sales Order</VOUCHERTYPENAME>
          <DATE>20260205</DATE>
          <PARTYLEDGERNAME>Raj Traders</PARTYLEDGERNAME>
          <NARRATION>February bulk order</NARRATION>
          <AMOUNT>25000.00</AMOUNT>
        </VOUCHER>
        <VOUCHER>
          <VOUCHERNUMBER>SO-2026-002</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Sales Order</VOUCHERTYPENAME>
          <DATE>20260210</DATE>
          <PARTYLEDGERNAME>Mehta &amp; Sons</PARTYLEDGERNAME>
          <NARRATION></NARRATION>
          <AMOUNT>18500.00</AMOUNT>
        </VOUCHER>
        <VOUCHER>
          <VOUCHERNUMBER>SO-2026-003</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Sales Order</VOUCHERTYPENAME>
          <DATE>20260214</DATE>
          <PARTYLEDGERNAME>Sharma General Store</PARTYLEDGERNAME>
          <NARRATION>Weekly supply</NARRATION>
          <AMOUNT>9800.00</AMOUNT>
        </VOUCHER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>"""

_PURCHASE_VOUCHERS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <VOUCHER>
          <VOUCHERNUMBER>PO-2026-001</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Purchase Order</VOUCHERTYPENAME>
          <DATE>20260203</DATE>
          <PARTYLEDGERNAME>Patel Wholesalers</PARTYLEDGERNAME>
          <NARRATION>Stock replenishment Q1</NARRATION>
          <AMOUNT>45000.00</AMOUNT>
        </VOUCHER>
        <VOUCHER>
          <VOUCHERNUMBER>PO-2026-002</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Purchase Order</VOUCHERTYPENAME>
          <DATE>20260211</DATE>
          <PARTYLEDGERNAME>Singh Distributors</PARTYLEDGERNAME>
          <NARRATION></NARRATION>
          <AMOUNT>22000.00</AMOUNT>
        </VOUCHER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>"""

_IMPORT_OK_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <IMPORTRESULT>
      <CREATED>1</CREATED>
    </IMPORTRESULT>
  </BODY>
</ENVELOPE>"""

_EMPTY_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><COLLECTION/></DATA></BODY></ENVELOPE>"""


# ── Request Dispatcher ────────────────────────────────────────────────────────

def _detect_request(body: bytes) -> str:
    """Read the XML body and return what kind of Tally request this is."""
    try:
        text = body.decode("utf-8", errors="replace")
        if "<TALLYREQUEST>Import Data</TALLYREQUEST>" in text:
            return "import"
        root = ET.fromstring(text)
        report = (root.findtext(".//REPORTNAME") or "").lower()
        voucher_type = (root.findtext(".//SVVOUCHERTYPE") or "").lower()
        if "list of companies" in report:
            return "companies"
        if "stock summary" in report:
            return "stock"
        if "list of accounts" in report:
            return "ledgers"
        if "voucher register" in report:
            if "purchase" in voucher_type:
                return "vouchers_purchase"
            return "vouchers_sales"
    except Exception:
        pass
    return "unknown"


_RESPONSES = {
    "companies":        _COMPANIES_XML,
    "stock":            _STOCK_XML,
    "ledgers":          _LEDGERS_XML,
    "vouchers_sales":   _SALES_VOUCHERS_XML,
    "vouchers_purchase":_PURCHASE_VOUCHERS_XML,
    "import":           _IMPORT_OK_XML,
}


# ── HTTP Handler ─────────────────────────────────────────────────────────────

class MockTallyHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # silence default access log
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length) if length else b""
        req_type = _detect_request(body)
        xml_out  = _RESPONSES.get(req_type, _EMPTY_XML)

        print(f"  ← POST  [{req_type:20s}]  {len(body)} bytes in / {len(xml_out)} bytes out")

        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(xml_out.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(xml_out.encode("utf-8"))

    def do_GET(self):
        msg = b"TallySync Mock Tally Server OK"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), MockTallyHandler)
    print(f"""
┌─────────────────────────────────────────────────────┐
│   TallySync  —  Mock Tally Prime Server             │
│                                                     │
│   Listening on  http://localhost:{PORT}               │
│   Returns realistic demo data (8 items, 7 ledgers)  │
│   Voucher push always succeeds                      │
│                                                     │
│   Press Ctrl+C to stop                              │
└─────────────────────────────────────────────────────┘
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
