from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app

AFTER_ALL_TEST_DATA = datetime(2027, 6, 1, tzinfo=UTC)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(config, "now", lambda: AFTER_ALL_TEST_DATA)
    with TestClient(app) as client:
        yield client
