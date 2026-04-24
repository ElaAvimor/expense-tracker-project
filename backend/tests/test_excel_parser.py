# ---------------- Unit Tests ------------------ #

from io import BytesIO
from openpyxl import Workbook

from services.excel_parser import InvalidImportSchemaError, parse_transactions_from_file


def _build_excel_file(rows: list[list]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "עסקאות במועד החיוב"

    headers = [
        "תאריך עסקה",
        "שם בית העסק",
        "קטגוריה",
        "סכום חיוב",
        "מטבע חיוב",
    ]

    sheet.append([])
    sheet.append([])
    sheet.append([])
    sheet.append(headers)

    for row in rows:
        sheet.append(row)

    file = BytesIO()
    workbook.save(file)
    return file.getvalue()


def test_parse_transactions_from_valid_excel():
    file_bytes = _build_excel_file([
        ["2026-04-24", "Test Merchant", "Food", 100.0, "ILS"],
    ])

    transactions, skipped_rows = parse_transactions_from_file(file_bytes)

    assert skipped_rows == 0
    assert transactions == [
        {
            "transaction_date": "2026-04-24",
            "merchant_name": "Test Merchant",
            "category": "Food",
            "amount": 100.0,
            "currency": "ILS",
        }
    ]


def test_parse_transactions_skips_invalid_rows():
    file_bytes = _build_excel_file([
        ["2026-04-24", "Valid Merchant", "Food", 100.0, "ILS"],
        ["2026-04-25", None, "Food", 50.0, "ILS"],
        ["2026-04-26", "Missing Amount", "Food", None, "ILS"],
    ])

    transactions, skipped_rows = parse_transactions_from_file(file_bytes)

    assert skipped_rows == 2
    assert transactions == [
        {
            "transaction_date": "2026-04-24",
            "merchant_name": "Valid Merchant",
            "category": "Food",
            "amount": 100.0,
            "currency": "ILS",
        }
    ]


def test_parse_transactions_invalid_file_raises_error():
    invalid_file_bytes = b"this is not an excel file"

    try:
        parse_transactions_from_file(invalid_file_bytes)
        assert False
    except InvalidImportSchemaError:
        assert True
