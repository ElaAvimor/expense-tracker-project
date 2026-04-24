from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Import, Transaction, Category, Merchant


def _resolve_dashboard_scope(mode: str, import_id: int | None, db: Session):
    """
    Set up scope configuration
    :param mode: "all", "import", or "latest"
    :param import_id: Unique file identifier
    :param db: Session to connect to the db
    :return:
    """
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
            return scope, target_import_id, True

    return scope, target_import_id, False


def _empty_dashboard_response() -> dict:
    """
    :return: dict representing an empty dashboard
    """
    return {
        "total_transactions": 0,
        "total_amount": 0,
        "spending_by_category": [],
        "scope": "latest",
        "import_id": None,
    }


def _get_dashboard_totals_and_spending(db: Session, target_import_id: int | None):
    """
    Get total transactions, total spending, total spending per category. If needed, filter by a specific imported file.
    :param db: Session to connect to db
    :param target_import_id: Unique file identifier
    :return: Total transactions, total spending, and spending per category
    """
    transaction_count_query = db.query(func.count(Transaction.id))
    total_amount_query = db.query(func.sum(Transaction.amount))
    category_total_amount_query = (
        db.query(
            Category.name.label("category_name"),
            func.sum(Transaction.amount).label("total_amount"),
        )
        .join(Category, Transaction.category_id == Category.id)
    )

    if target_import_id is not None:
        transaction_count_query = transaction_count_query.filter(Transaction.import_id == target_import_id)
        total_amount_query = total_amount_query.filter(Transaction.import_id == target_import_id)
        category_total_amount_query = category_total_amount_query.filter(Transaction.import_id == target_import_id)

    total_transactions = transaction_count_query.scalar()
    total_amount = total_amount_query.scalar() or 0
    spending_per_category = category_total_amount_query.group_by(Category.name).all()

    return total_transactions, total_amount, spending_per_category


def _get_top_category(spending_per_category, total_amount: int):
    """
    Get the category with the most expenditures.
    :param spending_per_category: Every category and how much was spent on it
    :param total_amount: Total spending amount
    :return: Top category's name, amount and % out of all spending
    """
    top_category = None
    if spending_per_category:
        top_row = max(spending_per_category, key=lambda row: row.total_amount)
        percent_spending = 0 if total_amount == 0 else round((top_row.total_amount / total_amount) * 100)
        top_category = {
            "category_name": top_row.category_name,
            "total_amount": top_row.total_amount,
            "percent_of_spending": percent_spending
        }
    return top_category


def _get_unusual_high_transactions(db: Session, target_import_id: int | None):
    """
    Get top 3 transactions with the highest spending
    :param db: Session to connet to db
    :param target_import_id: Unique import file identifier
    :return: List of top 3 highest transactions
    """
    transactions_query = (
        db.query(
            Merchant.name.label("merchant_name"),
            Transaction.amount.label("amount"),
            Transaction.transaction_date.label("transaction_date"),
        )
        .join(Merchant, Transaction.merchant_id == Merchant.id)
    )

    if target_import_id is not None:
        transactions_query = transactions_query.filter(
            Transaction.import_id == target_import_id
        )

    high_transactions_rows = (
        transactions_query
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

    return unusual_high_transactions


def get_dashboard_data(db: Session, mode: str = "latest", import_id: int | None = None):
    """
    Get all data to be displayed in dashboard: total spending, total transactions, top category, high transactions...
    :param mode: "all", "latest", or "import"
    :param import_id: Unique file identifier
    :param db: Session to connect to db
    :return: Dict holding all the data to be displayed
    """
    scope, target_import_id, should_return_empty = _resolve_dashboard_scope(mode, import_id, db)
    if should_return_empty:
        return _empty_dashboard_response()

    total_transactions, total_amount, spending_per_category = _get_dashboard_totals_and_spending(db, target_import_id)
    top_category = _get_top_category(spending_per_category, total_amount)
    unusual_high_transactions = _get_unusual_high_transactions(db, import_id)

    return {
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "spending_by_category": [
            {
                "category_name": category.category_name,
                "total_amount": category.total_amount,
            }
            for category in spending_per_category
        ],
        "scope": scope,
        "import_id": target_import_id,
        "top_category": top_category,
        "unusual_high_transactions": unusual_high_transactions,
    }