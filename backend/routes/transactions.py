from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.dependencies import get_db
from db.models import Transaction, Merchant, Category, Import

router = APIRouter()


@router.get("/transactions")
def get_transactions(import_id: int | None = None, db: Session = Depends(get_db)):
    query = (
        db.query(
            Transaction.id,
            Transaction.transaction_date,
            Transaction.amount,
            Transaction.currency,
            Transaction.description_raw,
            Transaction.import_id,
            Merchant.name.label("merchant_name"),
            Category.name.label("category_name"),
        )
        .join(Merchant, Transaction.merchant_id == Merchant.id)
        .join(Category, Transaction.category_id == Category.id)
    )

    if import_id is not None:
        query = query.filter(Transaction.import_id == import_id)

    rows = query.all()

    return [
        {
            "id": row.id,
            "transaction_date": row.transaction_date,
            "amount": row.amount,
            "currency": row.currency,
            "description_raw": row.description_raw,
            "import_id": row.import_id,
            "merchant_name": row.merchant_name,
            "category_name": row.category_name,
        }
        for row in rows
    ]


@router.get("/dashboard")
def get_dashboard(mode: str = "latest", import_id: int | None = None, db: Session = Depends(get_db)):
    scope = "all"
    target_import_id = None

    if import_id is not None:
        scope = "import"
        target_import_id = import_id
    elif mode == "latest":
        scope = "latest"
        latest = db.query(Import).order_by(Import.imported_at.desc()).first()
        if latest:
            target_import_id = latest.id
        else:
            return {
                "total_transactions": 0,
                "total_amount": 0,
                "spending_by_category": [],
                "scope": "latest",
                "import_id": None,
            }

    tx_count_q = db.query(func.count(Transaction.id))
    amt_q = db.query(func.sum(Transaction.amount))
    cat_q = (
        db.query(
            Category.name.label("category_name"),
            func.sum(Transaction.amount).label("total_amount"),
        )
        .join(Category, Transaction.category_id == Category.id)
    )

    if target_import_id is not None:
        tx_count_q = tx_count_q.filter(Transaction.import_id == target_import_id)
        amt_q = amt_q.filter(Transaction.import_id == target_import_id)
        cat_q = cat_q.filter(Transaction.import_id == target_import_id)

    total_transactions = tx_count_q.scalar()
    total_amount = amt_q.scalar() or 0
    spending_rows = cat_q.group_by(Category.name).all()

    return {
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "spending_by_category": [
            {
                "category_name": row.category_name,
                "total_amount": row.total_amount,
            }
            for row in spending_rows
        ],
        "scope": scope,
        "import_id": target_import_id,
    }