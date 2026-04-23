from collections import defaultdict
from datetime import datetime
from db.models import Transaction, Merchant
from sqlalchemy.orm import Session


def _find_baseline_amount(positive_txs: list[dict]) -> float | None:
    """Find the positive amount that appears in at least 3 different months.

    If multiple amounts qualify, pick the one with the most months,
    breaking ties by the lower amount (the established recurring charge).
    """
    amount_months: dict[float, set[tuple[int, int]]] = defaultdict(set)
    for t in positive_txs:
        month_key = (t["date"].year, t["date"].month)
        amount_months[t["amount"]].add(month_key)

    candidates = [
        (amount, len(months))
        for amount, months in amount_months.items()
        if len(months) >= 3
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda c: (-c[1], c[0]))
    return candidates[0][0]


def _detect_price_increase(merchant_name: str, baseline: float, positive_txs: list[dict]) -> dict | None:
    higher = [t for t in positive_txs if t["amount"] > baseline]
    if not higher:
        return None
    latest = higher[-1]
    return {
        "merchant_name": merchant_name,
        "latest_amount": latest["amount"],
        "previous_amount": baseline,
        "anomaly_type": "price_increase",
        "message": f"Recurring charge increased from {baseline} to {latest['amount']}",
    }


def _detect_duplicate_same_month(merchant_name: str, baseline: float, txs: list[dict]) -> dict | None:
    by_month: dict[tuple[int, int], list[float]] = defaultdict(list)
    for t in txs:
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
    rows = (
        db.query(
            Transaction.transaction_date,
            Transaction.amount,
            Merchant.name.label("merchant_name"),
        )
        .join(Merchant, Transaction.merchant_id == Merchant.id)
        .all()
    )

    by_merchant: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_merchant[row.merchant_name].append({
            "date": datetime.strptime(row.transaction_date, "%d-%m-%Y"),
            "amount": row.amount,
        })

    for txs in by_merchant.values():
        txs.sort(key=lambda t: t["date"])

    anomalies = []

    for merchant_name, txs in by_merchant.items():
        positive_txs = [t for t in txs if t["amount"] > 0]

        baseline = _find_baseline_amount(positive_txs)
        if baseline is None:
            continue

        price_inc = _detect_price_increase(merchant_name, baseline, positive_txs)
        if price_inc:
            anomalies.append(price_inc)

        duplicate = _detect_duplicate_same_month(merchant_name, baseline, txs)
        if duplicate:
            anomalies.append(duplicate)

    return anomalies
