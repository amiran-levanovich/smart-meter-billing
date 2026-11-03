from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, HTTPException, Path, Request
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app import config
from app.billing import NoReadingsError
from app.bills import bill_for_customer
from app.db import CustomerRecord
from app.schemas import BillOut, bill_out
from app.seed import seed_if_empty


def migrate(database_url: str) -> None:
    alembic_config = Config(config.BACKEND_DIR / "alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = config.database_url()
    migrate(database_url)
    engine = create_engine(database_url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    app.state.sessions = sessionmaker(engine)
    with app.state.sessions() as session:
        seed_if_empty(session, config.TASK_DIR / "readings.csv", config.TASK_DIR / "tariff.json")
    yield
    engine.dispose()


app = FastAPI(title="WattWunder Billing", lifespan=lifespan)


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.sessions() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def current_customer(session: SessionDep) -> CustomerRecord:
    customer = session.scalar(select(CustomerRecord).order_by(CustomerRecord.id).limit(1))
    if customer is None:
        raise HTTPException(404, "no customer")
    return customer


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/bill/{month}")
def get_bill(
    month: Annotated[str, Path(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
    session: SessionDep,
    customer: Annotated[CustomerRecord, Depends(current_customer)],
) -> BillOut:
    year, month_number = map(int, month.split("-"))
    try:
        bill = bill_for_customer(session, customer, year, month_number, config.prices_include_vat())
    except NoReadingsError:
        raise HTTPException(404, f"no readings for {month}") from None
    [meter] = customer.meters
    return bill_out(bill, month, customer.name, meter.meter_number)
