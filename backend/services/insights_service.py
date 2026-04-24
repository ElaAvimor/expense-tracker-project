from collections import defaultdict
from datetime import datetime
from db.models import Transaction, Merchant
from sqlalchemy.orm import Session


def _find_repeated_amount(positive_transactions: list[dict]) -> float | None:
    """
    Find the positive amount that appears in at least 3 different months.
    If multiple amounts qualify, pick the one with the most months,
    breaking ties by the lower amount (the established recurring charge).
    :param positive_transactions: a list of all positive transactions to compare
    :return: The lowest amount that was repeated in the most number of months (at least 3)
    """
    # amount_appearances = {100.0, {(2026, 04), (2026, 05)}
    amount_appearances: dict[float, set[tuple[int, int]]] = defaultdict(set)
    for transaction in positive_transactions:
        year_and_month = (transaction["date"].year, transaction["date"].month)
        amount_appearances[transaction["amount"]].add(year_and_month)

    # Amounts that appeared in at least 3 different months
    candidates = [
        (amount, len(months))
        for amount, months in amount_appearances.items()
        if len(months) >= 3
    ]
    if not candidates:
        return None

    # Pick the candidate amount with the most months and lowest amount and then return that amount
    candidates.sort(key=lambda c: (-c[1], c[0]))
    return candidates[0][0]


def _detect_price_increase(merchant_name: str, baseline: float, positive_transactions: list[dict]) -> dict | None:
    """
    Get positive transactions and a base and find the latest recurring charge that had a price increase
    :param merchant_name:
    :param baseline:
    :param positive_transactions:
    :return:
    """
    transaction_higher_than_base = [t for t in positive_transactions if t["amount"] > baseline]
    if not transaction_higher_than_base:
        return None

    latest = transaction_higher_than_base[-1]
    return {
        "merchant_name": merchant_name,
        "latest_amount": latest["amount"],
        "previous_amount": baseline,
        "anomaly_type": "price_increase",
        "message": f"Recurring charge increased from {baseline} to {latest['amount']}",
    }


def _detect_duplicate_same_month(merchant_name: str, baseline: float, transactions: list[dict]) -> dict | None:
    """
    Get a list of transactions, a merchant and a baseline and check if there are any duplicates
    :param merchant_name: The name of merchant in the transaction
    :param baseline: The amount to be duplicated
    :param transactions: The list of transactions to check
    :return: Duplicated transactions if found
    """
    by_month: dict[tuple[int, int], list[float]] = defaultdict(list)
    for t in transactions:
        month_key = (t["date"].year, t["date"].month)
        by_month[month_key].append(t["amount"])

    for amounts in by_month.values():
        positives = [a for a in amounts if a == baseline]
        negatives = [abs(a) for a in amounts if a == -baseline]

        unmatched = list(positives)
        for neg in negatives:
            refund = abs(neg)
            if refund in unmatched:
                unmatched.remove(refund)

        if len(unmatched) >= 2:
            return {
                "merchant_name": merchant_name,
                "latest_amount": baseline,
                "previous_amount": baseline,
                "anomaly_type": "duplicate_same_month",
                "message": f"{merchant_name} was charged more than once in the same month",
            }

    return None


def find_recurring_anomalies(db: Session) -> list[dict]:
    """
    Query the db and find any transactions that appear at least 3 times with the same merchant and amount
    :param db: The session for querying the db
    :return: List of recurring anomalies
    """
    transactions = (
        db.query(
            Transaction.transaction_date,
            Transaction.amount,
            Merchant.name.label("merchant_name"),
        )
        .join(Merchant, Transaction.merchant_id == Merchant.id)
        .all()
    )
    transactions_by_merchant = defaultdict(list)
    anomalies = []

    # Group transactions by merchant
    for row in transactions:
        transactions_by_merchant[row.merchant_name].append({
            "date": datetime.strptime(row.transaction_date, "%d-%m-%Y"),
            "amount": row.amount,
        })

    # For each merchant, sort its transactions by date
    for transactions in transactions_by_merchant.values():
        transactions.sort(key=lambda t: t["date"])

    for merchant_name, transaction in transactions_by_merchant.items():
        positive_transactions = [t for t in transaction if t["amount"] > 0]

        # Find the amount that was repeated in the most months (at least 3), if exists
        repeated = _find_repeated_amount(positive_transactions)
        if repeated is None:
            continue

        # Find a repeated amount that had a charge increase, if exists
        price_increase = _detect_price_increase(merchant_name, repeated, positive_transactions)
        if price_increase:
            anomalies.append(price_increase)

        # Find a repeated amount that appeared more than once in the same month, if exists
        duplicate = _detect_duplicate_same_month(merchant_name, repeated, transaction)
        if duplicate:
            anomalies.append(duplicate)

    return anomalies
