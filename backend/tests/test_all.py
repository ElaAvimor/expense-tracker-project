# integration tests - if the FE calls a route, will it return the right status code, shape, and DB effect?

from datetime import datetime, timezone
from db.models import Category, Import, Merchant, Transaction


# --- transactions ---
def test_get_dashboard_empty(client) -> None:
    """
    Test that the dashboard route returns the correct response when there are no transactions.
    :param client: The test client, injected by pytest.
    :return: None
    """
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.json() == {
        "total_transactions": 0,
        "total_amount": 0,
        "spending_by_category": [],
        "scope": "latest",
        "import_id": None,
    }


def test_get_dashboard_with_transactions(client, db_session) -> None:
    """
    Test that the dashboard route returns the correct response when there are transactions.
    :param client: The test client, injected by pytest.
    :param db_session: The database session, injected by pytest.
    :return: None
    """
    imported_file = Import(id=1, file_name="test.xlsx", file_hash="1234567890", imported_at=datetime.now(timezone.utc))
    merchant = Merchant(id=1, name="Test Merchant")
    category = Category(id=1, name="Test Category")

    db_session.add_all([imported_file, merchant, category])
    db_session.commit()

    transaction = Transaction(
        amount=100.0,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="2026-04-13",
        currency="ILS",
        description_raw="Test Transaction",
    )
    db_session.add(transaction)
    db_session.commit()

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.json() == {
        "total_transactions": 1,
        "total_amount": 100,
        "spending_by_category": [{"category_name": "Test Category", "total_amount": 100}],
        "scope": "latest",
        "import_id": 1,
    }


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


# --- insights ---
def test_get_recurring_anomalies_return_200(client, db_session) -> None:
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


# --- imports ---
def test_confirm_import_saves_transactions(client, db_session) -> None:
    request_body = {
        "filename": "test.xlsx",
        "file_hash": "abc123",
        "transactions": [
            {
                "transaction_date": "10-04-2026",
                "merchant_name": "Netflix",
                "category": "Entertainment",
                "amount": 54.9,
                "currency": "ILS",
            },
            {
                "transaction_date": "11-04-2026",
                "merchant_name": "Superpharm",
                "category": "Health",
                "amount": 80.0,
                "currency": "ILS",
            },
        ],
    }

    response = client.post("/imports/confirm", json=request_body)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Import confirmed successfully",
        "import_id": 1,
        "transactions_count": 2,
    }

    imports = db_session.query(Import).all()
    merchants = db_session.query(Merchant).all()
    categories = db_session.query(Category).all()
    transactions = db_session.query(Transaction).all()

    assert len(imports) == 1
    assert len(merchants) == 2
    assert len(categories) == 2
    assert len(transactions) == 2
