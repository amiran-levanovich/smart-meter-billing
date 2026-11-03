import random
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.billing import BERLIN, Reading, month_intervals
from app.db import MeterRecord
from app.ingest import IngestResult, ingest_readings
from app.seed import SEED_METER_PUBLIC_ID, read_csv

DEMO_MONTHS = [(2026, 8), (2026, 9), (2026, 11), (2027, 1)]


def demo_readings(
    october: list[Reading], year: int, month: int, rng: random.Random
) -> list[Reading]:
    latest = {r.interval_start: r.energy_wh for r in october}
    profile: defaultdict[tuple, list[int]] = defaultdict(list)
    for t in sorted(latest):
        local = t.astimezone(BERLIN)
        profile[(local.weekday(), local.time())].append(latest[t])
    readings = []
    for t in month_intervals(year, month):
        local = t.astimezone(BERLIN)
        values = profile[(local.weekday(), local.time())]
        base = values[(local.day - 1) // 7 % len(values)]
        readings.append(Reading(t, round(base * rng.uniform(0.95, 1.05))))
    return readings


def seed_demo(session: Session) -> IngestResult:
    meter = session.scalars(
        select(MeterRecord).where(MeterRecord.public_id == SEED_METER_PUBLIC_ID)
    ).one()
    october = read_csv(config.REPO_DIR / "readings.csv")
    rng = random.Random(2026)
    readings = [r for year, month in DEMO_MONTHS for r in demo_readings(october, year, month, rng)]
    result = ingest_readings(session, meter.id, readings, datetime.now(UTC))
    session.commit()
    return result
