from fastapi import Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from routes.transactions import router
from services.build_dashboard import get_dashboard_data


@router.get("/dashboard")
def get_dashboard(mode: str = "latest", import_id: int | None = None, db: Session = Depends(get_db)):
    return get_dashboard_data(mode, import_id, db)
