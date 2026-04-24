# ---------------- Integrations Tests ------------------ #
from datetime import datetime, timezone

from db.models import Import, Merchant, Category, Transaction


def test_get_transactions_filtered_by_import_id(client, db_session) -> None:
    """
    Test that the transactions route returns the correct response when filtered by import id.
    :param client: The test client, injected by pytest.
    :param db_session: The database session, injected by pytest.
    :return: None
    """
    imported_file1 = Import(
        id=1,
        file_name="test.xlsx",
        file_hash="1234567890",
        imported_at=datetime.now(timezone.utc)
    )
    imported_file2 = Import(
        id=2,
        file_name="test2.xlsx",
        file_hash="1234567891",
        imported_at=datetime.now(timezone.utc))
    merchant = Merchant(id=1, name="Test Merchant")
    category = Category(id=1, name="Test Category")

    transaction1 = Transaction(
        amount=100.0,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="2026-04-13",
        currency="ILS",
        description_raw="Test Transaction"
    )

    transaction2 = Transaction(
        amount=200.0,
        category_id=1,
        merchant_id=1,
        import_id=2,
        transaction_date="2026-04-14",
        currency="ILS",
        description_raw="Test Transaction 2"
    )

    db_session.add_all([
        imported_file1,
        imported_file2,
        merchant,
        category,
        transaction1,
        transaction2,
    ])
    db_session.commit()
    db_session.refresh(transaction1)

    response = client.get("/transactions?import_id=1")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": transaction1.id,
            "transaction_date": "2026-04-13",
            "amount": 100.0,
            "currency": "ILS",
            "description_raw": "Test Transaction",
            "import_id": 1,
            "merchant_name": "Test Merchant",
            "category_name": "Test Category",
        }
    ]


def test_get_transactions_latest_scope(client, db_session):
    """
    Test that the transactions route returns the correct response when filtered by latest scope
    :param client: The test client, injected by pytest.
    :param db_session: The database session, injected by pytest.
    :return: None
    """
    imported_file1 = Import(
        id=1,
        file_name="test.xlsx",
        file_hash="1234567890",
        imported_at=datetime.now(timezone.utc)
    )
    imported_file2 = Import(
        id=2,
        file_name="test2.xlsx",
        file_hash="1234567891",
        imported_at=datetime.now(timezone.utc))
    merchant = Merchant(id=1, name="Test Merchant")
    category = Category(id=1, name="Test Category")

    transaction1 = Transaction(
        amount=100.0,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="2026-04-13",
        currency="ILS",
        description_raw="Test Transaction"
    )

    transaction2 = Transaction(
        amount=200.0,
        category_id=1,
        merchant_id=1,
        import_id=2,
        transaction_date="2026-04-14",
        currency="ILS",
        description_raw="Test Transaction 2"
    )

    db_session.add_all([
        imported_file1,
        imported_file2,
        merchant,
        category,
        transaction1,
        transaction2,
    ])
    db_session.commit()
    db_session.refresh(transaction1)

    response = client.get("/transactions?import_id=2")
    assert response.status_code == 200
    assert response.json() == [
        {
            "id": transaction2.id,
            "transaction_date": "2026-04-14",
            "amount": 200.0,
            "currency": "ILS",
            "description_raw": "Test Transaction 2",
            "import_id": 2,
            "merchant_name": "Test Merchant",
            "category_name": "Test Category",
        }
    ]
