from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]
from db.dependencies import get_db
from services.insights_service import find_recurring_anomalies

router = APIRouter()


@router.get("/insights/recurring-anomalies")
def get_recurring_anomalies(db: Session = Depends(get_db)):
    return find_recurring_anomalies(db)
