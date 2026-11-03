from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing import Bill, Reading, Tariff, compute_bill, month_bounds
from app.db import CustomerRecord, ReadingCorrectionRecord, ReadingRecord


def bill_for_customer(
    session: Session, customer: CustomerRecord, year: int, month: int, prices_include_vat: bool
) -> Bill:
    [meter] = customer.meters
    record = customer.tariff
    tariff = Tariff(
        record.day_start,
        record.day_end,
        record.day_ct_per_kwh,
        record.night_ct_per_kwh,
        record.monthly_fee_eur,
    )
    readings = load_readings(session, meter.id, *month_bounds(year, month))
    return compute_bill(readings, tariff, year, month, prices_include_vat=prices_include_vat)


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

    latest_superseded = (
        select(
            ReadingCorrectionRecord.interval_start,
            func.max(ReadingCorrectionRecord.superseded_at).label("superseded_at"),
        )
        .where(
            ReadingCorrectionRecord.meter_id == meter_id,
            ReadingCorrectionRecord.interval_start >= start,
            ReadingCorrectionRecord.interval_start < end,
        )
        .group_by(ReadingCorrectionRecord.interval_start)
        .subquery()
    )
    previous = {
        row.interval_start: row.energy_wh
        for row in session.scalars(
            select(ReadingCorrectionRecord)
            .join(
                latest_superseded,
                (ReadingCorrectionRecord.interval_start == latest_superseded.c.interval_start)
                & (ReadingCorrectionRecord.superseded_at == latest_superseded.c.superseded_at),
            )
            .where(ReadingCorrectionRecord.meter_id == meter_id)
        )
    }
    return [
        Reading(row.interval_start, row.energy_wh, previous.get(row.interval_start))
        for row in [*before, *in_month, *after]
    ]
