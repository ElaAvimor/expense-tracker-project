from fastapi.testclient import TestClient # lets tests send HTTP requests to the app and validate the responses.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from main import app # we import the app so that TestClient can send requests to it.
from db.database import Base # we import the base so that tests db can use the same models as the app.
from db.dependencies import get_db # we need to import the get_db dependency so that we can override it for testing.

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# whenever the app calls get_db, it will use our override_get_db function instead.
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db_session():
    db = TestingSessionLocal() # create a new db session for the test
    try:
        yield db
    finally:
        db.close()