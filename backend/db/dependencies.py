from db.database import SessionLocal # creates a new db session for each request


def get_db():
    db = SessionLocal()
    try:
        yield db  # gives the db session to the request
    finally:
        db.close()
