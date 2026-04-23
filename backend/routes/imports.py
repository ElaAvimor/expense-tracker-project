from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from services.excel_parser import parse_transactions_from_file
from services.save_transactions import save_parsed_transactions
from services.file_hash import calculate_file_hash
from db.dependencies import get_db
from db.models import Import, Transaction

router = APIRouter() # creates group of routes


def _build_period_label(min_date_str: str | None, max_date_str: str | None) -> str | None:
    """
    Derive a human-friendly period label from YYYY-MM-DD date strings.
    :param min_date_str: The start date of the period.
    :param max_date_str: The end date of the period.
    :return: A human-friendly period label, or None if the dates are invalid.
    """
    if not min_date_str or not max_date_str:
        return None
    try:
        min_d = datetime.strptime(min_date_str, "%Y-%m-%d")
        max_d = datetime.strptime(max_date_str, "%Y-%m-%d")
    except ValueError:
        return None

    if min_d.year == max_d.year and min_d.month == max_d.month:
        return min_d.strftime("%B %Y")  # e.g. "April 2026"

    if min_d.year == max_d.year:
        return f"{min_d.strftime('%B')} – {max_d.strftime('%B %Y')}"  # e.g. "March – April 2026"

    return f"{min_d.strftime('%b %Y')} – {max_d.strftime('%b %Y')}"  # e.g. "Dec 2025 – Jan 2026"


class ParsedTransaction(BaseModel):
    transaction_date: str
    merchant_name: str
    category: str | None = None
    amount: float
    currency: str | None = None


class ConfirmImportRequest(BaseModel):
    filename: str
    file_hash: str
    transactions: list[ParsedTransaction]


@router.get("/imports")
def list_imports(db: Session = Depends(get_db)) -> list[dict]:
    """
    Gets all imports from the database and returns a list of imports with their date ranges, to be displayed in the UI.
    :param db: The database session, injected by FastAPI.
    :return: A list of imports with their date ranges.
    """
    rows = db.query(Import).order_by(Import.imported_at.desc()).all()

    sortable_date = (
        func.substr(Transaction.transaction_date, 7, 4) + "-" +
        func.substr(Transaction.transaction_date, 4, 2) + "-" +
        func.substr(Transaction.transaction_date, 1, 2)
    )
    date_ranges = (
        db.query(
            Transaction.import_id,
            func.min(sortable_date).label("min_date"),
            func.max(sortable_date).label("max_date"),
        )
        .group_by(Transaction.import_id)
        .all()
    )
    range_map = {r.import_id: (r.min_date, r.max_date) for r in date_ranges}

    result = []
    for row in rows:
        min_d, max_d = range_map.get(row.id, (None, None))
        result.append({
            "id": row.id,
            "file_name": row.file_name,
            "imported_at": row.imported_at.isoformat() if row.imported_at else None,
            "period_label": _build_period_label(min_d, max_d),
        })
    return result

@router.delete("/imports/{import_id}")
def delete_import(import_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Deletes an import and all associated transactions from the database.
    :param import_id: The id of the import to delete.
    :param db: The database session, injected by FastAPI.
    :return: A success message.
    """
    imp = db.query(Import).filter(Import.id == import_id).first()
    if not imp:
        raise HTTPException(status_code=404, detail="Import not found")

    db.query(Transaction).filter(Transaction.import_id == import_id).delete()
    db.delete(imp)
    db.commit()

    return {"message": "Import deleted successfully", "import_id": import_id} # todo: what if deletion fails?

@router.post("/imports/preview")
def preview_import(file: UploadFile = File(...)) -> dict:
    """
    Parses the excel file and returns the transactions for preview.
    Does not save anything to the database.
    """
    file_bytes = file.file.read()
    file_hash = calculate_file_hash(file_bytes)
    parsed_transactions, skipped_rows_count = parse_transactions_from_file(file_bytes)

    return {
        "filename": file.filename,
        "file_hash": file_hash,
        "transactions": parsed_transactions,
        "skipped_rows_count": skipped_rows_count,
    }

@router.post("/imports/confirm")
def confirm_import(request: ConfirmImportRequest, db: Session = Depends(get_db)) -> dict: # FastAPI sees Depends(get_db) and injects the db session into the request for us
    parsed_transactions = [transaction.model_dump() for transaction in request.transactions]

    try:
        imported_file_row = save_parsed_transactions(db, request.filename, request.file_hash, parsed_transactions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Import confirmed successfully",
        "import_id": imported_file_row.id,
        "transactions_count": len(parsed_transactions),
    }