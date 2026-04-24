from sqlalchemy.orm import Session

from db.models import Transaction, Merchant, Category


def get_saved_transactions(db: Session, import_id: int | None = None) -> list[dict]:
    """
    Get all existing transactions from db, filter by a specific import if needed, and return relevant data
    :param db: Session to interact with db
    :param import_id: Unique file identifier if user wants transactions of a specific file, or None if user wants all transactions
    :return: List of requested transactions
    """
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
