import random
from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.billing import BERLIN, INTERVAL, Reading, month_intervals
from app.db import MeterRecord
from app.ingest import IngestResult, ingest_readings
from app.seed import SEED_METER_PUBLIC_ID, read_csv

TASK_MONTH = (2026, 10)


def months_back(year: int, month: int, count: int) -> list[tuple[int, int]]:
    return [divmod(year * 12 + month - 1 - k, 12) for k in range(count, 0, -1)]


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


def seed_demo(session: Session, now: datetime) -> IngestResult:
    meter = session.scalars(
        select(MeterRecord).where(MeterRecord.public_id == SEED_METER_PUBLIC_ID)
    ).one()
    october = read_csv(config.REPO_DIR / "readings.csv")
    rng = random.Random(2026)
    local_now = now.astimezone(BERLIN)
    past = [(y, m + 1) for y, m in months_back(local_now.year, local_now.month, 6)]
    gap = past[2]
    readings = [
        r
        for year, month in past
        if (year, month) not in (TASK_MONTH, gap)
        for r in demo_readings(october, year, month, rng)
    ] + [
        r
        for r in demo_readings(october, local_now.year, local_now.month, rng)
        if r.interval_start + INTERVAL <= now
    ]
    result = ingest_readings(session, meter.id, readings, datetime.now(UTC))
    session.commit()
    return result
