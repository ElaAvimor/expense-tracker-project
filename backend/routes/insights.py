from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session  # pyright: ignore[reportMissingImports]
from db.dependencies import get_db
from services.insights_service import find_recurring_anomalies

router = APIRouter()


@router.get("/insights/recurring-anomalies")
def get_recurring_anomalies(db: Session = Depends(get_db)) -> list[dict]:
    """
    Get transactions that appear in at least 3 different files with the same merchant and amount
    :param db: The db session to communicate with db
    :return: A list of recurring anomalies as described above
    """
    return find_recurring_anomalies(db)
