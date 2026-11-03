import json

from app.config import REPO_DIR
from app.main import app


def test_committed_openapi_schema_is_current():
    committed = json.loads((REPO_DIR / "frontend" / "openapi.json").read_text())
    assert committed == app.openapi(), "API changed: run `make types` and commit the result"
