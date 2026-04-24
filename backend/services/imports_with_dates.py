from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime

from db.models import Import, Transaction


def _build_date_label(min_date_str: str | None, max_date_str: str | None) -> str | None:
    """
    Derive a human-friendly date label from YYYY-MM-DD date strings.
    :param min_date_str: The start date of the period.
    :param max_date_str: The end date of the period.
    :return: A human-friendly date label, or None if the dates are invalid.
    """
    if not min_date_str or not max_date_str:
        return None
    try:
        min_d = datetime.strptime(min_date_str, "%Y-%m-%d")
        max_d = datetime.strptime(max_date_str, "%Y-%m-%d")
    except ValueError:
        return None

    # All transactions in the file are from the same month and year
    if min_d.year == max_d.year and min_d.month == max_d.month:
        return min_d.strftime("%B %Y")  # e.g. "April 2026"

    # All transactions in the file are from the same year, but there is a range of months
    if min_d.year == max_d.year:
        return f"{min_d.strftime('%B')} – {max_d.strftime('%B %Y')}"  # e.g. "March – April 2026"

    # There is a range of years and months
    return f"{min_d.strftime('%b %Y')} – {max_d.strftime('%b %Y')}"  # e.g. "Dec 2025 – Jan 2026"


def prepare_import_list(db: Session) -> list[dict]:
    """
    Matches a date period for each imported file currently in the db
    :param db: The session to interact with the db, injected by FastAPI
    :return: List of dicts where each one holds the file name and id, imported date, and period label
    """
    imports_by_upload_date = db.query(Import).order_by(Import.imported_at.desc()).all()

    # Converts date string from "DD-MM-YYYY" to "YYY-MM-DD" because that format can be sorted correctly as text
    sortable_date = (
            func.substr(Transaction.transaction_date, 7, 4) + "-" +
            func.substr(Transaction.transaction_date, 4, 2) + "-" +
            func.substr(Transaction.transaction_date, 1, 2)
    )

    # Extracts the min and max dates
    date_ranges = (
        db.query(
            Transaction.import_id,
            func.min(sortable_date).label("min_date"),
            func.max(sortable_date).label("max_date"),
        )
        .group_by(Transaction.import_id)
        .all()
    )

    # Map file id to its min and max dates
    range_map = {r.import_id: (r.min_date, r.max_date) for r in date_ranges}

    result = []
    for imp in imports_by_upload_date:
        min_d, max_d = range_map.get(imp.id, (None, None))
        result.append({
            "id": imp.id,
            "file_name": imp.file_name,
            "imported_at": imp.imported_at.isoformat() if imp.imported_at else None,
            "period_label": _build_date_label(min_d, max_d),
        })

    return result
