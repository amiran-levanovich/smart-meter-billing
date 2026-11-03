from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing import Reading
from app.db import ReadingCorrectionRecord, ReadingRecord


@dataclass(frozen=True)
class IngestResult:
    inserted: int
    corrected: int
    unchanged: int


def ingest_readings(
    session: Session, meter_id: int, readings: Iterable[Reading], received_at: datetime
) -> IngestResult:
    readings = list(readings)
    if not readings:
        return IngestResult(0, 0, 0)
    starts = [r.interval_start for r in readings]
    stored = {
        row.interval_start: row
        for row in session.scalars(
            select(ReadingRecord).where(
                ReadingRecord.meter_id == meter_id,
                ReadingRecord.interval_start.between(min(starts), max(starts)),
            )
        )
    }

    inserted = corrected = unchanged = 0
    for reading in readings:
        row = stored.get(reading.interval_start)
        if row is None:
            row = ReadingRecord(
                meter_id=meter_id,
                interval_start=reading.interval_start,
                energy_wh=reading.energy_wh,
                received_at=received_at,
            )
            session.add(row)
            stored[reading.interval_start] = row
            inserted += 1
        elif row.energy_wh == reading.energy_wh:
            unchanged += 1
        else:
            session.add(
                ReadingCorrectionRecord(
                    meter_id=meter_id,
                    interval_start=row.interval_start,
                    energy_wh=row.energy_wh,
                    received_at=row.received_at,
                    superseded_at=received_at,
                )
            )
            row.energy_wh = reading.energy_wh
            row.received_at = received_at
            corrected += 1
    session.flush()
    return IngestResult(inserted, corrected, unchanged)
