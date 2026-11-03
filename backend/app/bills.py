from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing import Bill, Reading, compute_bill, month_bounds
from app.db import ReadingRecord, ReplacedReadingRecord, TariffRecord


def bill_for_meter(
    session: Session,
    meter_id: int,
    tariff: TariffRecord,
    year: int,
    month: int,
    prices_include_vat: bool,
) -> Bill:
    readings = load_readings(session, meter_id, *month_bounds(year, month))
    return compute_bill(
        readings, tariff.to_tariff(), year, month, prices_include_vat=prices_include_vat
    )


def load_readings(session: Session, meter_id: int, start: datetime, end: datetime) -> list[Reading]:
    of_meter = ReadingRecord.meter_id == meter_id
    in_month = session.scalars(
        select(ReadingRecord).where(
            of_meter, ReadingRecord.interval_start >= start, ReadingRecord.interval_start < end
        )
    ).all()
    before = session.scalars(
        select(ReadingRecord)
        .where(of_meter, ReadingRecord.interval_start < start)
        .order_by(ReadingRecord.interval_start.desc())
        .limit(1)
    ).all()
    after = session.scalars(
        select(ReadingRecord)
        .where(of_meter, ReadingRecord.interval_start >= end)
        .order_by(ReadingRecord.interval_start)
        .limit(1)
    ).all()

    replaced_wh = {
        row.interval_start: row.energy_wh
        for row in session.scalars(
            select(ReplacedReadingRecord)
            .where(
                ReplacedReadingRecord.meter_id == meter_id,
                ReplacedReadingRecord.interval_start >= start,
                ReplacedReadingRecord.interval_start < end,
            )
            .order_by(ReplacedReadingRecord.id)
        )
    }
    return [
        Reading(row.interval_start, row.energy_wh, replaced_wh.get(row.interval_start))
        for row in [*before, *in_month, *after]
    ]
