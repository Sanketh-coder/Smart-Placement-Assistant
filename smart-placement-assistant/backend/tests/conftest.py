import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_tmp = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["AUTO_SEED"] = "true"

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, pw):
    r = client.post("/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return _login(client, "admin@example.com", "Admin_password")


@pytest.fixture(scope="session")
def student(client):
    return _login(client, "student@example.com", "Student_password")
