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
    top_category = None

    if import_id is not None:
        scope = "import"
        target_import_id = import_id
    elif mode == "latest":
        scope = "latest"
        latest = db.query(Import).order_by(Import.imported_at.desc()).first()
        if latest:
            target_import_id = latest.id
        else:
            #  Dashboard mode is 'latest' but there are no imported files in the db
            return {
                "total_transactions": 0,
                "total_amount": 0,
                "spending_by_category": [],
                "scope": "latest",
                "import_id": None,
            }

    transaction_count_query = db.query(func.count(Transaction.id))
    total_amount_query = db.query(func.sum(Transaction.amount))
    category_total_amount_query = (
        db.query(
            Category.name.label("category_name"),
            func.sum(Transaction.amount).label("total_amount"),
        )
        .join(Category, Transaction.category_id == Category.id)
    )

    #  A specific import is selected to be shown
    if target_import_id is not None:
        transaction_count_query = transaction_count_query.filter(Transaction.import_id == target_import_id)
        total_amount_query = total_amount_query.filter(Transaction.import_id == target_import_id)
        category_total_amount_query = category_total_amount_query.filter(Transaction.import_id == target_import_id)

    total_transactions = transaction_count_query.scalar()
    total_amount = total_amount_query.scalar() or 0
    spending_rows = category_total_amount_query.group_by(Category.name).all()

    if spending_rows:
        top_row = max(spending_rows, key=lambda row: row.total_amount)
        percent_spending = 0 if total_amount == 0 else round((top_row.total_amount / total_amount) * 100)
        top_category = {
            "category_name": top_row.category_name,
            "total_amount": top_row.total_amount,
            "percent_of_spending": percent_spending
        }

    high_transactions_query = (
        db.query(
            Merchant.name.label("merchant_name"),
            Transaction.amount.label("amount"),
            Transaction.transaction_date.label("transaction_date"),
        )
        .join(Merchant, Transaction.merchant_id == Merchant.id)
    )

    if target_import_id is not None:
        high_transactions_query = high_transactions_query.filter(
            Transaction.import_id == target_import_id
        )

    high_transactions_rows = (
        high_transactions_query
        .order_by(Transaction.amount.desc())
        .limit(3)
        .all()
    )

    unusual_high_transactions = [
        {
            "merchant_name": row.merchant_name,
            "amount": row.amount,
            "transaction_date": row.transaction_date,
        }
        for row in high_transactions_rows
    ]

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
        "top_category": top_category,
        "unusual_high_transactions": unusual_high_transactions,
    }
