import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends, FastAPI, HTTPException, Path, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

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


MAX_READINGS = 31 * 24 * 4
MAX_BODY_BYTES = 1_000_000

app = FastAPI(title="WattWunder Billing", lifespan=lifespan)


@app.middleware("http")
async def limit_body_size(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    if int(request.headers.get("content-length", 0)) > MAX_BODY_BYTES:
        return JSONResponse({"detail": "request body too large"}, status_code=413)
    return await call_next(request)


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
    public_id: uuid.UUID, readings: list[ReadingIn], session: SessionDep
) -> IngestOut:
    if len(readings) > MAX_READINGS:
        raise HTTPException(413, f"at most {MAX_READINGS} readings per request")
    meter = session.scalar(select(MeterRecord).where(MeterRecord.public_id == public_id))
    if meter is None:
        raise HTTPException(404, "unknown meter")
    result = ingest_readings(
        session, meter.id, (r.to_reading() for r in readings), datetime.now(UTC)
    )
    session.commit()
    return IngestOut.model_validate(result, from_attributes=True)
