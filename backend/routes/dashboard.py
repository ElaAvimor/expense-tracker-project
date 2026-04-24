from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from services.build_dashboard import get_dashboard_data

router = APIRouter()  # creates group of routes

@router.get("/dashboard")
def get_dashboard(mode: str = "latest", import_id: int | None = None, db: Session = Depends(get_db)):
    return get_dashboard_data(db, mode, import_id)
