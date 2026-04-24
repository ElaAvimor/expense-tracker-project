from fastapi import UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi import APIRouter, Depends

from db.dependencies import get_db
from services.excel_parser import parse_transactions_from_file, InvalidImportSchemaError
from services.file_hash import calculate_file_hash
from services.save_transactions import save_parsed_transactions
from services.delete_import import delete_import_and_related_transactions

router = APIRouter()  # creates group of routes


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


@router.post("/imports/preview")
def parse_import(file: UploadFile = File(...)) -> dict:
    """
    Parses the Excel file and returns the transactions for preview.
    Does not save anything to the database.
    :param file: The Excel file to parse and preview
    :return: file name, hash, transactions list, and the number of skipped rows from the file.
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Invalid file format. Expected .xlsx")

    file_bytes = file.file.read()
    file_hash = calculate_file_hash(file_bytes)

    try:
        parsed_transactions, skipped_rows_count = parse_transactions_from_file(file_bytes)
    except InvalidImportSchemaError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "filename": file.filename,
        "file_hash": file_hash,
        "transactions": parsed_transactions,
        "skipped_rows_count": skipped_rows_count,
    }


@router.post("/imports/confirm")
def confirm_import(request: ConfirmImportRequest, db: Session = Depends(get_db)) -> dict:
    """
    Receives a file name, file hash and a list of parsed transactions and saves them in the db
    :param request: A ConfirmImportRequest object: holds the file name and hash and the parsed transactions
    :param db: The session to communicate with db
    :return: Success message, import id and the total count of transactions that were saved.
    """
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


@router.delete("/imports/{import_id}")
def delete_import(import_id: int, db: Session = Depends(get_db)) -> dict:
    """
    Deletes an import and all associated transactions from the database.
    :param import_id: The id of the import to delete.
    :param db: The database session, injected by FastAPI.
    :return: A success message. Or raise an HTTPException if import file was not found.
    """
    is_deleted = delete_import_and_related_transactions(import_id, db)
    if not is_deleted:
        raise HTTPException(status_code=404, detail="Import not found")

    return {"message": "Import deleted successfully", "import_id": import_id}
