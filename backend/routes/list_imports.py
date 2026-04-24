from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from services.imports_with_dates import prepare_import_list

router = APIRouter()  # creates group of routes


@router.get("/imports")
def list_imports(db: Session = Depends(get_db)) -> list[dict]:
    """
    Gets all imports from the database and returns a list of imports with their date ranges, to be displayed in the UI.
    :param db: The database session, injected by FastAPI.
    :return: A list of imports with their date ranges.
    """
    imports_with_date_range = prepare_import_list(db)
    return imports_with_date_range


