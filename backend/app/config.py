import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent


def database_url() -> str:
    return os.environ.get("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'billing.db'}")


def prices_include_vat() -> bool:
    return os.environ.get("PRICES_INCLUDE_VAT", "true").lower() == "true"
