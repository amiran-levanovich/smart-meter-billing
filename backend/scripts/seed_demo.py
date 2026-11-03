from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import config
from app.demo import seed_demo
from app.main import migrate
from app.seed import seed_if_empty

database_url = config.database_url()
migrate(database_url)
with Session(create_engine(database_url)) as session:
    seed_if_empty(session, config.REPO_DIR / "readings.csv", config.REPO_DIR / "tariff.json")
    print(seed_demo(session))
