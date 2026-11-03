import csv
import json
import uuid
from datetime import UTC, datetime, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing import BERLIN, Reading
from app.db import CustomerRecord, MeterRecord, TariffRecord
from app.ingest import ingest_readings

SEED_METER_PUBLIC_ID = uuid.UUID("3f6c1a52-8e0b-4b7e-9a51-2d4f7c9e0b18")
SEED_METER_NUMBER = "1EBZ0100123456"
SEED_CUSTOMER_NAME = "Bäckerei Sonnenschein"


class NonexistentLocalTimeError(ValueError):
    pass


def seed_if_empty(session: Session, readings_csv: Path, tariff_json: Path) -> None:
    if session.scalar(select(CustomerRecord.id).limit(1)) is not None:
        return
    raw = json.loads(tariff_json.read_text(), parse_float=Decimal)
    tariff = TariffRecord(
        name="Tag/Nacht-Tarif",
        day_start=time.fromisoformat(raw["day"]["from"]),
        day_end=time.fromisoformat(raw["day"]["to"]),
        day_ct_per_kwh=raw["day"]["ct_per_kwh"],
        night_ct_per_kwh=raw["night"]["ct_per_kwh"],
        monthly_fee_eur=raw["monthly_fee_eur"],
    )
    customer = CustomerRecord(name=SEED_CUSTOMER_NAME, tariff=tariff)
    meter = MeterRecord(
        public_id=SEED_METER_PUBLIC_ID, meter_number=SEED_METER_NUMBER, customer=customer
    )
    session.add(meter)
    session.flush()
    ingest_readings(session, meter.id, read_csv(readings_csv), received_at=datetime.now(UTC))
    session.commit()


def read_csv(path: Path) -> list[Reading]:
    seen: set[datetime] = set()
    readings = []
    with path.open(newline="") as file:
        for row in csv.DictReader(file):
            naive = datetime.fromisoformat(row["timestamp"])
            local = to_berlin(naive, second_occurrence=naive in seen)
            seen.add(naive)
            readings.append(Reading(local.astimezone(UTC), int(row["energy_wh"])))
    return readings


def to_berlin(naive: datetime, second_occurrence: bool) -> datetime:
    first, second = (naive.replace(tzinfo=BERLIN, fold=fold) for fold in (0, 1))
    if first.astimezone(UTC).astimezone(BERLIN).replace(tzinfo=None) != naive:
        raise NonexistentLocalTimeError(f"{naive} does not exist in Europe/Berlin")
    ambiguous = first.utcoffset() != second.utcoffset()
    return second if ambiguous and second_occurrence else first
