"""
TallySync Manager — Unit Tests: XML Parser
Run from the server/ directory:
    python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tally.xml_parser import (
    _parse_xml,
    _strip_invalid_char_refs,
    parse_companies,
    parse_stock_items,
    parse_ledgers,
    parse_vouchers,
    parse_import_response,
)


# ─── _parse_xml ──────────────────────────────────────────────────────────────

class TestParseXml:
    def test_valid_xml(self):
        xml = "<ROOT><ITEM>hello</ITEM></ROOT>"
        result = _parse_xml(xml)
        assert result == {"ROOT": {"ITEM": "hello"}}

    def test_returns_empty_dict_on_broken_xml(self):
        result = _parse_xml("<broken<xml>")
        assert result == {}

    def test_strips_invalid_control_characters(self):
        # chr(0x01) and chr(0x08) are invalid in XML 1.0
        xml = f"<ROOT><NAME>Test\x01Company\x08Name</NAME></ROOT>"
        result = _parse_xml(xml)
        # Should not raise and should parse with chars stripped
        assert result != {}
        assert "ROOT" in result

    def test_strips_invalid_char_entity_refs(self):
        # &#8; = backspace, &#x1C; = file separator — both invalid in XML 1.0
        xml = "<ROOT><NAME>Item&#8;Name&#x1C;Here</NAME></ROOT>"
        result = _parse_xml(xml)
        assert result != {}
        assert result["ROOT"]["NAME"] == "ItemNameHere"

    def test_keeps_valid_char_entity_refs(self):
        # &#65; = 'A', &#x26; = '&amp;' — valid, must be preserved
        xml = "<ROOT><NAME>&#65;mpersand</NAME></ROOT>"
        result = _parse_xml(xml)
        assert result["ROOT"]["NAME"] == "Ampersand"

    def test_strip_invalid_char_refs_decimal(self):
        assert _strip_invalid_char_refs("Hello&#8;World") == "HelloWorld"

    def test_strip_invalid_char_refs_hex(self):
        assert _strip_invalid_char_refs("Hello&#x1C;World") == "HelloWorld"

    def test_strip_invalid_char_refs_keeps_valid(self):
        # &#9; = tab (valid), &#10; = newline (valid)
        s = "Tab&#9;here&#10;newline"
        assert _strip_invalid_char_refs(s) == s

    def test_allows_valid_whitespace_chars(self):
        xml = "<ROOT>\n  <ITEM>\t hello \t</ITEM>\n</ROOT>"
        result = _parse_xml(xml)
        assert "ROOT" in result

    def test_empty_string(self):
        result = _parse_xml("")
        assert result == {}


# ─── parse_companies ─────────────────────────────────────────────────────────

COMPANIES_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <COMPANY><NAME>Alpha Traders</NAME></COMPANY>
        <COMPANY><NAME>Beta Exports</NAME></COMPANY>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""

COMPANIES_SINGLE_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <COMPANY><NAME>Solo Corp</NAME></COMPANY>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""


class TestParseCompanies:
    def test_parses_multiple_companies(self):
        result = parse_companies(COMPANIES_XML)
        assert result == ["Alpha Traders", "Beta Exports"]

    def test_parses_single_company(self):
        result = parse_companies(COMPANIES_SINGLE_XML)
        assert result == ["Solo Corp"]

    def test_empty_response_returns_empty_list(self):
        result = parse_companies("<ENVELOPE></ENVELOPE>")
        assert result == []

    def test_broken_xml_returns_empty_list(self):
        result = parse_companies("not xml at all")
        assert result == []


# ─── parse_stock_items ───────────────────────────────────────────────────────

STOCK_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <STOCKITEM>
          <NAME>Steel Rods</NAME>
          <PARENT>Metal Group</PARENT>
          <BASEUNITS>KGS</BASEUNITS>
          <CLOSINGBALANCE>500.0000</CLOSINGBALANCE>
          <CLOSINGVALUE>250000.00</CLOSINGVALUE>
        </STOCKITEM>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""


class TestParseStockItems:
    def test_parses_basic_stock_item(self):
        items = parse_stock_items(STOCK_XML)
        assert len(items) == 1
        item = items[0]
        assert item["tally_name"] == "Steel Rods"
        assert item["group_name"] == "Metal Group"
        assert item["uom"] == "KGS"
        assert item["closing_qty"] == 500.0
        assert item["closing_value"] == 250000.0
        assert item["rate"] == round(250000.0 / 500.0, 4)

    def test_zero_qty_does_not_divide(self):
        xml = """<ENVELOPE><BODY><DATA><COLLECTION>
          <STOCKITEM><NAME>Empty</NAME><CLOSINGBALANCE>0</CLOSINGBALANCE><CLOSINGVALUE>0</CLOSINGVALUE></STOCKITEM>
        </COLLECTION></DATA></BODY></ENVELOPE>"""
        items = parse_stock_items(xml)
        assert items[0]["rate"] == 0.0

    def test_empty_xml_returns_empty(self):
        assert parse_stock_items("<ENVELOPE></ENVELOPE>") == []


# ─── parse_ledgers ───────────────────────────────────────────────────────────

LEDGERS_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <LEDGER>
          <NAME>ABC Pvt Ltd</NAME>
          <PARENT>Sundry Debtors</PARENT>
          <OPENINGBALANCE>10000</OPENINGBALANCE>
          <CLOSINGBALANCE>15000</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>XYZ Suppliers</NAME>
          <PARENT>Sundry Creditors</PARENT>
          <OPENINGBALANCE>5000</OPENINGBALANCE>
          <CLOSINGBALANCE>8000</CLOSINGBALANCE>
        </LEDGER>
        <LEDGER>
          <NAME>Cash</NAME>
          <PARENT>Cash-in-hand</PARENT>
          <OPENINGBALANCE>0</OPENINGBALANCE>
          <CLOSINGBALANCE>1000</CLOSINGBALANCE>
        </LEDGER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""


class TestParseLedgers:
    def test_customer_ledger_type(self):
        ledgers = parse_ledgers(LEDGERS_XML)
        abc = next(l for l in ledgers if l["tally_name"] == "ABC Pvt Ltd")
        assert abc["ledger_type"] == "CUSTOMER"

    def test_supplier_ledger_type(self):
        ledgers = parse_ledgers(LEDGERS_XML)
        xyz = next(l for l in ledgers if l["tally_name"] == "XYZ Suppliers")
        assert xyz["ledger_type"] == "SUPPLIER"

    def test_other_ledger_type(self):
        ledgers = parse_ledgers(LEDGERS_XML)
        cash = next(l for l in ledgers if l["tally_name"] == "Cash")
        assert cash["ledger_type"] == "OTHER"

    def test_balances_parsed(self):
        ledgers = parse_ledgers(LEDGERS_XML)
        abc = next(l for l in ledgers if l["tally_name"] == "ABC Pvt Ltd")
        assert abc["opening_balance"] == 10000.0
        assert abc["closing_balance"] == 15000.0

    def test_empty_xml_returns_empty(self):
        assert parse_ledgers("<ENVELOPE></ENVELOPE>") == []


# ─── parse_vouchers ──────────────────────────────────────────────────────────

VOUCHERS_XML = """
<ENVELOPE>
  <BODY>
    <DATA>
      <COLLECTION>
        <VOUCHER>
          <VOUCHERNUMBER>SO-001</VOUCHERNUMBER>
          <VOUCHERTYPENAME>Sales Order</VOUCHERTYPENAME>
          <DATE>20240115</DATE>
          <PARTYLEDGERNAME>ABC Pvt Ltd</PARTYLEDGERNAME>
          <NARRATION>Test order</NARRATION>
          <AMOUNT>-50000</AMOUNT>
        </VOUCHER>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
"""


class TestParseVouchers:
    def test_parses_voucher(self):
        vouchers = parse_vouchers(VOUCHERS_XML)
        assert len(vouchers) == 1
        v = vouchers[0]
        assert v["voucher_number"] == "SO-001"
        assert v["voucher_type"] == "Sales Order"
        assert v["party_name"] == "ABC Pvt Ltd"
        assert v["amount"] == 50000.0   # abs value

    def test_date_parsed(self):
        from datetime import date
        vouchers = parse_vouchers(VOUCHERS_XML)
        assert vouchers[0]["voucher_date"] == date(2024, 1, 15)

    def test_amount_is_always_positive(self):
        vouchers = parse_vouchers(VOUCHERS_XML)
        assert vouchers[0]["amount"] >= 0

    def test_empty_returns_empty(self):
        assert parse_vouchers("<ENVELOPE></ENVELOPE>") == []


# ─── parse_import_response ───────────────────────────────────────────────────

class TestParseImportResponse:
    def test_success_created_1(self):
        xml = """<ENVELOPE><BODY><IMPORTRESULT><CREATED>1</CREATED></IMPORTRESULT></BODY></ENVELOPE>"""
        success, msg, vnum = parse_import_response(xml)
        assert success is True

    def test_failure_line_error(self):
        xml = """<ENVELOPE><BODY><DATA><LINEERROR>Ledger not found</LINEERROR></DATA></BODY></ENVELOPE>"""
        success, msg, vnum = parse_import_response(xml)
        assert success is False
        assert "Ledger not found" in msg

    def test_broken_xml_returns_false(self):
        success, msg, vnum = parse_import_response("garbage")
        assert success is False


# ─── xml_builder integration ─────────────────────────────────────────────────

class TestXmlBuilder:
    """Verify that xml_builder produces parseable XML."""

    def test_get_companies_is_valid_xml(self):
        from tally.xml_builder import build_get_companies
        xml = build_get_companies()
        result = _parse_xml(xml)
        assert "ENVELOPE" in result

    def test_get_stock_items_is_valid_xml(self):
        from tally.xml_builder import build_get_stock_items
        xml = build_get_stock_items("Test Company")
        result = _parse_xml(xml)
        assert "ENVELOPE" in result

    def test_get_ledgers_is_valid_xml(self):
        from tally.xml_builder import build_get_ledgers
        xml = build_get_ledgers("Test Company")
        result = _parse_xml(xml)
        assert "ENVELOPE" in result

    def test_push_sales_order_is_valid_xml(self):
        from datetime import date
        from tally.xml_builder import build_push_sales_order, OrderLineData
        line = OrderLineData(
            stock_item_name="Steel Rods",
            quantity=10.0,
            rate=500.0,
            amount=5000.0,
            uom="KGS",
            is_sales=True,
        )
        xml = build_push_sales_order(
            company_name="Test Co",
            order_number="SO-001",
            order_date=date(2024, 1, 15),
            party_name="ABC Pvt Ltd",
            lines=[line],
            narration="Test",
        )
        result = _parse_xml(xml)
        assert "ENVELOPE" in result

    def test_tally_date_format(self):
        from datetime import date
        from tally.xml_builder import build_get_vouchers
        from_d = date(2024, 1, 1)
        to_d   = date(2024, 1, 31)
        xml = build_get_vouchers("Test Co", "Sales Order", from_d, to_d)
        assert "20240101" in xml
        assert "20240131" in xml
