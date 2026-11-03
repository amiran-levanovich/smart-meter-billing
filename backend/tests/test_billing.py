"""Trap tests for the billing core. Expected values are worked out by hand from the
task's tariff (day 31.847 ct/kWh 06:00-22:00, night 19.392 ct/kWh, fee 12.90 EUR)."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.billing import Reading, Tariff, compute_bill

BERLIN = ZoneInfo("Europe/Berlin")
TARIFF = Tariff(
    day_start=time(6, 0),
    day_end=time(22, 0),
    day_ct_per_kwh=Decimal("31.847"),
    night_ct_per_kwh=Decimal("19.392"),
    monthly_fee_eur=Decimal("12.90"),
)


def month_readings(year: int, month: int, energy_wh: int = 0) -> dict[datetime, int]:
    """Every interval of the Berlin calendar month, keyed by UTC start."""
    start = datetime(year, month, 1, tzinfo=BERLIN).astimezone(UTC)
    next_month = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=BERLIN).astimezone(UTC)
    readings = {}
    t = start
    while t < next_month:
        readings[t] = energy_wh
        t += timedelta(minutes=15)
    return readings


def berlin(*args: int, fold: int = 0) -> datetime:
    return datetime(*args, tzinfo=BERLIN, fold=fold).astimezone(UTC)


def bill_for(readings: dict[datetime, int], year: int = 2026, month: int = 10, **kwargs):
    return compute_bill(
        [Reading(t, wh) for t, wh in readings.items()], TARIFF, year, month, **kwargs
    )


def line(bill, kind: str):
    return next(item for item in bill.lines if item.kind == kind)


def test_interval_is_priced_by_its_start_in_berlin_local_time():
    readings = month_readings(2026, 10)
    for hour, minute in [(5, 45), (6, 0), (21, 45), (22, 0)]:
        readings[berlin(2026, 10, 1, hour, minute)] = 1000

    bill = bill_for(readings)

    # 06:00 and 21:45 are day; 05:45 and 22:00 are night
    assert line(bill, "day").quantity == Decimal("2.000")
    assert line(bill, "night").quantity == Decimal("2.000")
