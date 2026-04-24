# ---------------- Integrations Tests ------------------ #

from datetime import datetime, timezone

from db.models import Import, Merchant, Category, Transaction


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
        "spending_by_category": [{"category_name": "Test Category", "total_amount": 100.0}],
        "scope": "latest",
        "import_id": 1,
        "top_category":  {
            "category_name": "Test Category",
            "total_amount": 100.0,
            "percent_of_spending": 100
        },
        "unusual_high_transactions": [{
            "merchant_name": "Test Merchant",
            "amount": 100.0,
            "transaction_date": "2026-04-13",
        }]
    }


def test_dashboard_with_latest_scope(client, db_session) -> None:
    """
    Check that when having more than one import and filtering by latest, the dashboard presents the latest only
    :param client: The test client, injected by pytest
    :param db_session: DB session, injected by pytest
    :return: None
    """
    imported_file_1 = Import(id=1, file_name="test1.xlsx", file_hash="hash1", imported_at=datetime.now(timezone.utc))
    merchant_1 = Merchant(id=1, name="Test Merchant1")
    category_1 = Category(id=1, name="Test Category1")

    db_session.add_all([imported_file_1, merchant_1, category_1])
    db_session.commit()

    transaction = Transaction(
        amount=100.0,
        category_id=1,
        merchant_id=1,
        import_id=1,
        transaction_date="2026-04-24",
        currency="ILS",
        description_raw="Test Transaction1",
    )
    db_session.add(transaction)
    db_session.commit()

    imported_file_2 = Import(id=2, file_name="test2.xlsx", file_hash="hash2", imported_at=datetime.now(timezone.utc))
    merchant_2 = Merchant(id=2, name="Test Merchant2")
    category_2 = Category(id=2, name="Test Category2")

    db_session.add_all([imported_file_2, merchant_2, category_2])
    db_session.commit()

    transaction = Transaction(
        amount=200.0,
        category_id=2,
        merchant_id=2,
        import_id=2,
        transaction_date="2026-04-24",
        currency="ILS",
        description_raw="Test Transaction2",
    )
    db_session.add(transaction)
    db_session.commit()

    response = client.get("/dashboard")
    assert response.status_code == 200
    assert response.json() == {
        "total_transactions": 1,
        "total_amount": 200.0,
        "spending_by_category": [{"category_name": "Test Category2", "total_amount": 200.0}],
        "scope": "latest",
        "import_id": 2,
        "top_category": {
            "category_name": "Test Category2",
            "total_amount": 200.0,
            "percent_of_spending": 100
        },
        "unusual_high_transactions": [
            {
                "merchant_name": "Test Merchant2",
                "amount": 200.0,
                "transaction_date": "2026-04-24",
            },
            {
                'amount': 100.0,
                'merchant_name': 'Test Merchant1',
                'transaction_date': '2026-04-24',
            },
        ]
    }
