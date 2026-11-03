import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, HTTPException, Path, Request
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import config
from app.billing import NoReadingsError
from app.bills import bill_for_meter
from app.db import CustomerRecord, MeterRecord
from app.ingest import ingest_readings
from app.schemas import BillOut, IngestOut, ReadingIn, bill_out
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
        seed_if_empty(session, config.REPO_DIR / "readings.csv", config.REPO_DIR / "tariff.json")
    yield
    engine.dispose()


MAX_READINGS = 31 * 96 + 4
MAX_BODY_BYTES = 1_000_000


class BodySizeLimit:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            received += len(message.get("body", b""))
            if received > MAX_BODY_BYTES:
                raise HTTPException(413, f"request body exceeds {MAX_BODY_BYTES} bytes")
            return message

        await self.app(scope, limited_receive, send)


app = FastAPI(title="WattWunder Billing", lifespan=lifespan)
app.add_middleware(BodySizeLimit)


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.sessions() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def current_customer(session: SessionDep) -> CustomerRecord:
    customer = session.scalar(select(CustomerRecord).order_by(CustomerRecord.id).limit(1))
    if customer is None:
        raise HTTPException(404, "no customer")
    return customer


def meter_by_public_id(public_id: uuid.UUID, session: SessionDep) -> MeterRecord:
    meter = session.scalar(select(MeterRecord).where(MeterRecord.public_id == public_id))
    if meter is None:
        raise HTTPException(404, "unknown meter")
    return meter


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
    [meter] = customer.meters
    try:
        bill = bill_for_meter(
            session, meter.id, customer.tariff, year, month_number, config.prices_include_vat()
        )
    except NoReadingsError:
        raise HTTPException(404, f"no readings for {month}") from None
    return bill_out(bill, month, customer.name, meter.meter_number)


@app.post("/api/meters/{public_id}/readings")
def post_readings(
    readings: list[ReadingIn],
    session: SessionDep,
    meter: Annotated[MeterRecord, Depends(meter_by_public_id)],
) -> IngestOut:
    if len(readings) > MAX_READINGS:
        raise HTTPException(413, f"at most {MAX_READINGS} readings per request")
    result = ingest_readings(
        session, meter.id, (r.to_reading() for r in readings), datetime.now(UTC)
    )
    session.commit()
    return IngestOut.model_validate(result, from_attributes=True)
