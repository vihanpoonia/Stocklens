import os, sys
os.environ["DATABASE_URL"] = "sqlite:///./test_stocklens.db"
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import json, pytest
from fastapi.testclient import TestClient
from app.core.database import SessionLocal
from app.seed.generate import generate
from app.services import refresh_ratios

@pytest.fixture(scope="session", autouse=True)
def seeded():
    ids = generate(seed=7, labels_path="/tmp/anomaly_labels_test.json")
    with SessionLocal() as s:
        refresh_ratios(s)
    return ids

@pytest.fixture(scope="session")
def client(seeded):
    from app.main import app
    return TestClient(app)

@pytest.fixture()
def db():
    s = SessionLocal()
    yield s
    s.close()
