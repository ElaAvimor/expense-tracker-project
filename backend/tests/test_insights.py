# ---------------- Integrations Tests ------------------ #

from datetime import datetime, timezone

from db.models import Import, Merchant, Category, Transaction


def test_recurring_anomalies_detects_price_increase(client, db_session) -> None:
    """
    Test that the recurring anomalies route returns the correct response when there are no anomalies.
    :param client: The test client, injected by pytest.
    :param db_session: The database session, injected by pytest.
    :return: None
    """
    imported_file = Import(
        id=1,
        file_name="test.xlsx",
        file_hash="123456",
        imported_at=datetime.now(timezone.utc),
    )
    merchant = Merchant(id=1, name="Netflix")
    category = Category(id=1, name="Entertainment")

    tx1 = Transaction(
        amount=54.9,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="10-01-2026",
        currency="ILS",
        description_raw="Netflix January",
    )
    tx2 = Transaction(
        amount=54.9,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="10-02-2026",
        currency="ILS",
        description_raw="Netflix February",
    )
    tx3 = Transaction(
        amount=54.9,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="10-03-2026",
        currency="ILS",
        description_raw="Netflix March",
    )
    tx4 = Transaction(
        amount=64.9,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="10-04-2026",
        currency="ILS",
        description_raw="Netflix April",
    )

    db_session.add_all([imported_file, merchant, category, tx1, tx2, tx3, tx4])
    db_session.commit()

    response = client.get("/insights/recurring-anomalies")

    assert response.status_code == 200
    assert response.json() == [
        {
            "merchant_name": "Netflix",
            "latest_amount": 64.9,
            "previous_amount": 54.9,
            "anomaly_type": "price_increase",
            "message": "Recurring charge increased from 54.9 to 64.9",
        }
    ]


def test_recurring_anomalies_returns_empty_when_no_repeated_charge(client, db_session) -> None:
    """
    Check that no recurring anomalies appear when there is no repeated charge
    :param client: The test client, injected by pytest.
    :param db_session: The database session, injected by pytest.
    :return: None
    """
    imported_file = Import(
        id=1,
        file_name="test.xlsx",
        file_hash="123456",
        imported_at=datetime.now(timezone.utc),
    )
    merchant = Merchant(id=1, name="Netflix")
    category = Category(id=1, name="Entertainment")

    transaction = Transaction(
        amount=54.9,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="10-01-2026",
        currency="ILS",
        description_raw="Netflix January",
    )

    db_session.add_all([imported_file, merchant, category, transaction])
    db_session.commit()

    response = client.get("/insights/recurring-anomalies")

    assert response.status_code == 200
    assert response.json() == []

