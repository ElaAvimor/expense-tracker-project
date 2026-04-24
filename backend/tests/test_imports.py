# ---------------- Integrations Tests ------------------ #

from db.models import Import, Merchant, Category, Transaction


def test_confirm_import_saves_transactions(client, db_session) -> None:
    """
    Check that the confirm endpoint saves the transaction in the db correctly
    :param client: The test client, injected by Pytest
    :param db_session: The db session, injected by Pytest
    :return: None
    """
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


def test_confirm_import_duplicate_file_hash_is_rejected(client, db_session) -> None:
    """
    Check that when trying to import a file that already exists, it gets rejected.
    :param client: The test client, injected by Pytest
    :param db_session: The db session, injected by Pytest
    :return: None
    """
    request_body1 = {
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

    response1 = client.post("/imports/confirm", json=request_body1)

    request_body2 = {
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

    response2 = client.post("/imports/confirm", json=request_body2)

    assert response1.status_code == 200
    assert response2.status_code == 400
