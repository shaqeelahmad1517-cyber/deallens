"""Tests for the DealLens document ingestion primitive."""
import pytest

from documents import extract_from_rows, extract_from_text, invoke, parse_number


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("1,200,000", 1_200_000),
    ("$520,000", 520_000),
    ("(45,000)", -45_000),
    ("-45000", -45_000),
    ("1.5m", 1_500_000),
    ("830k", 830_000),
    ("2.1bn", 2_100_000_000),
    ("12%", None),
    ("", None),
    ("n/a", None),
    (1234, 1234.0),
])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


# ---------------------------------------------------------------------------
# Row extraction
# ---------------------------------------------------------------------------
def test_extract_core_fields_from_rows():
    rows = [
        ["Line item", "FY2023"],
        ["Total Revenue", "4,200,000"],
        ["Net Income", "520,000"],
        ["Interest expense", "40,000"],
        ["Income tax expense", "110,000"],
        ["Depreciation", "90,000"],
        ["Amortization", "20,000"],
        ["Owner compensation", "180,000"],
        ["Total assets", "1,900,000"],
        ["Total liabilities", "700,000"],
    ]
    out = extract_from_rows(rows)
    f = out["financials"]
    assert f["revenue"] == 4_200_000
    assert f["net_income"] == 520_000
    assert f["interest"] == 40_000
    assert f["taxes"] == 110_000
    assert f["depreciation"] == 90_000
    assert f["amortization"] == 20_000
    assert f["owner_compensation"] == 180_000
    assert f["total_assets"] == 1_900_000
    assert f["total_liabilities"] == 700_000
    assert out["warnings"] == []


def test_revenue_excludes_cost_of_sales():
    rows = [["Cost of sales", "1,000,000"], ["Net sales", "3,000,000"]]
    out = extract_from_rows(rows)
    assert out["financials"].get("revenue") == 3_000_000


def test_picks_rightmost_year_column():
    rows = [["Revenue", "3,000,000", "3,500,000", "4,200,000"]]
    out = extract_from_rows(rows)
    assert out["financials"]["revenue"] == 4_200_000


def test_adjustment_candidates_flagged():
    rows = [["Owner's personal vehicle", "35,000"], ["One-time legal settlement", "60,000"]]
    out = extract_from_rows(rows)
    labels = [a["label"] for a in out["adjustment_candidates"]]
    assert any("vehicle" in l.lower() for l in labels)
    assert any("one-time" in l.lower() for l in labels)


def test_missing_required_warns():
    out = extract_from_rows([["Depreciation", "90,000"]])
    assert any("revenue" in w for w in out["warnings"])
    assert any("net_income" in w for w in out["warnings"])


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def test_extract_from_pasted_text():
    text = """
    Revenue ................ 4,200,000
    Net income ............. 520,000
    Total assets ........... 1,900,000
    """
    out = extract_from_text(text)
    assert out["financials"]["revenue"] == 4_200_000
    assert out["financials"]["net_income"] == 520_000


def test_text_single_line_label_value():
    out = extract_from_text("Owner salary 180000")
    assert out["financials"]["owner_compensation"] == 180_000


# ---------------------------------------------------------------------------
# Primitive contract
# ---------------------------------------------------------------------------
def test_invoke_with_csv_text():
    env = invoke({"csv_text": "Revenue,4200000\nNet income,520000\n"})
    assert env["ok"] is True
    assert env["result"]["financials"]["revenue"] == 4_200_000


def test_invoke_requires_an_input():
    env = invoke({})
    assert env["ok"] is False
    assert env["error"]["type"] == "ValueError"


def test_invoke_xlsx_roundtrip(tmp_path):
    # Build a tiny xlsx with openpyxl if available; else skip.
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Total Revenue", 4200000])
    ws.append(["Net Income", 520000])
    p = tmp_path / "fin.xlsx"
    wb.save(str(p))
    env = invoke({"path": str(p)})
    assert env["ok"]
    assert env["result"]["financials"]["revenue"] == 4_200_000


def test_determinism():
    p = {"csv_text": "Revenue,4200000\nNet income,520000\n"}
    assert invoke(p) == invoke(p)


# ---------------------------------------------------------------------------
# Hardening: silent-error regression tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("1.234.567,89", 1234567.89),   # European: dot thousands, comma decimal
    ("1.234,56", 1234.56),          # European decimal
    ("1.234.567", 1234567),         # European thousands, no decimal
    ("12,50", 12.5),                # comma decimal
    ("4,200", 4200),                # US thousands
    ("1,234.50", 1234.5),           # US decimal
    ("520000-", -520000),           # trailing minus
    ("−520000", -520000),      # unicode minus
])
def test_parse_number_locale_and_signs(raw, expected):
    assert parse_number(raw) == expected


def test_thousands_scale_applied_and_warned():
    out = extract_from_text("($ in thousands)\nRevenue 4,200\nNet income 520")
    assert out["financials"]["revenue"] == 4_200_000
    assert out["financials"]["net_income"] == 520_000
    assert any("thousands" in w for w in out["warnings"])


def test_millions_scale():
    out = extract_from_text("(in millions)\nRevenue 4.2\nNet income 0.52")
    assert out["financials"]["revenue"] == pytest.approx(4_200_000)


def test_net_loss_is_negative():
    assert extract_from_text("Net loss (300,000)")["financials"]["net_income"] == -300_000
    # even shown as a positive number, a loss is negative
    assert extract_from_text("Net loss 300,000")["financials"]["net_income"] == -300_000


def test_contra_revenue_not_mistaken_for_revenue():
    assert extract_from_rows([["Sales returns and allowances", "120,000"],
                              ["Total revenue", "4,200,000"]])["financials"]["revenue"] == 4_200_000
    assert extract_from_rows([["Other revenue", "50,000"],
                              ["Total revenue", "4,200,000"]])["financials"]["revenue"] == 4_200_000


def test_footnote_column_not_picked_as_value():
    out = extract_from_rows([["Revenue", "4,200,000", "3"]])
    assert out["financials"]["revenue"] == 4_200_000


def test_multi_year_warns():
    out = extract_from_rows([["Revenue", "5,000,000", "4,200,000"]])
    assert any("Multiple value columns" in w for w in out["warnings"])


def test_xlsx_without_cell_refs(tmp_path):
    # Hand-written xlsx where cells omit the 'r' attribute must not collapse to col 0.
    import zipfile
    content_types = ('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
                     'package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/>'
                     '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-'
                     'officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/'
                     'sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.'
                     'worksheet+xml"/></Types>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    wb = ('<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
          '<sheets><sheet name="S1" sheetId="1"/></sheets></workbook>')
    # cells deliberately have NO r="" attribute, and inline strings
    sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/'
             'main"><sheetData><row><c t="inlineStr"><is><t>Total Revenue</t></is></c><c t="n"><v>4200000</v>'
             '</c></row><row><c t="inlineStr"><is><t>Net Income</t></is></c><c t="n"><v>520000</v></c></row>'
             '</sheetData></worksheet>')
    p = tmp_path / "noref.xlsx"
    with zipfile.ZipFile(str(p), "w") as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", wb)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    env = invoke({"path": str(p)})
    assert env["ok"]
    assert env["result"]["financials"]["revenue"] == 4_200_000
    assert env["result"]["financials"]["net_income"] == 520_000


def test_docx_tables_and_paragraphs(tmp_path):
    import zipfile
    doc = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
        '<w:p><w:r><w:t>Financial Statement FY2023</w:t></w:r></w:p>'
        '<w:tbl>'
        '<w:tr><w:tc><w:p><w:r><w:t>Total Revenue</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>4,200,000</w:t></w:r></w:p></w:tc></w:tr>'
        '<w:tr><w:tc><w:p><w:r><w:t>Net Income</w:t></w:r></w:p></w:tc>'
        '<w:tc><w:p><w:r><w:t>520,000</w:t></w:r></w:p></w:tc></w:tr>'
        '</w:tbl>'
        '<w:p><w:r><w:t>Owner salary 180,000</w:t></w:r></w:p>'
        '</w:body></w:document>'
    )
    p = tmp_path / "statement.docx"
    with zipfile.ZipFile(str(p), "w") as z:
        z.writestr("word/document.xml", doc)
    env = invoke({"path": str(p)})
    assert env["ok"]
    f = env["result"]["financials"]
    assert f["revenue"] == 4_200_000
    assert f["net_income"] == 520_000
    assert f["owner_compensation"] == 180_000
