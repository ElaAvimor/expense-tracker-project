from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from services.get_existing_transactions import get_saved_transactions

router = APIRouter()


@router.get("/transactions")
def get_transactions(import_id: int | None = None, db: Session = Depends(get_db)):
    return get_saved_transactions(db, import_id)
