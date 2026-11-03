"""Trap tests for the billing core. Expected values are worked out by hand from the
task's tariff (day 31.847 ct/kWh 06:00-22:00, night 19.392 ct/kWh, fee 12.90 EUR)."""

from dataclasses import replace
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


def test_fall_back_day_bills_both_repeated_hours_at_night_price():
    readings = month_readings(2026, 10)
    for fold in (0, 1):
        for minute in (0, 15, 30, 45):
            readings[berlin(2026, 10, 25, 2, minute, fold=fold)] = 1000

    bill = bill_for(readings)

    assert line(bill, "night").quantity == Decimal("8.000")
    assert line(bill, "day").quantity == Decimal("0.000")


def test_month_with_fall_back_has_100_intervals_on_that_day():
    bill = bill_for(month_readings(2026, 10, energy_wh=1000))

    # 31 days x 64 day intervals; 2980 intervals in total
    assert line(bill, "day").quantity == Decimal("1984.000")
    assert line(bill, "night").quantity == Decimal("996.000")


def test_month_with_spring_forward_has_92_intervals_on_that_day():
    bill = bill_for(month_readings(2027, 3, energy_wh=1000), year=2027, month=3)

    # 28 Mar 2027 loses 02:00-03:00, a night hour: 2972 intervals in total
    assert line(bill, "day").quantity == Decimal("1984.000")
    assert line(bill, "night").quantity == Decimal("988.000")


def test_clock_change_is_a_notice_at_the_first_interval_after_it():
    bill = bill_for(month_readings(2026, 10))

    assert [(n.kind, n.interval_start) for n in bill.notices] == [
        ("dst", datetime.fromisoformat("2026-10-25T02:00:00+01:00"))
    ]


def test_each_line_is_rounded_to_cents_and_the_total_is_their_sum():
    bill = bill_for(month_readings(2026, 10, energy_wh=1000))

    # 1984 kWh x 31.847 ct = 631.84448; 996 kWh x 19.392 ct = 193.14432
    assert [item.amount_eur for item in bill.lines] == [
        Decimal("631.84"),
        Decimal("193.14"),
        Decimal("12.90"),
    ]
    # rounding the unrounded sum once would give 837.89
    assert bill.total_eur == Decimal("837.88")


def test_half_a_cent_rounds_up():
    readings = month_readings(2026, 10)
    readings[berlin(2026, 10, 1, 12, 0)] = 50  # 0.05 kWh x 10 ct = 0.5 ct

    bill = compute_bill(
        [Reading(t, wh) for t, wh in readings.items()],
        replace(TARIFF, day_ct_per_kwh=Decimal("10")),
        2026,
        10,
    )

    assert line(bill, "day").amount_eur == Decimal("0.01")


def test_gross_prices_show_the_included_vat():
    bill = bill_for(month_readings(2026, 10, energy_wh=1000))

    assert bill.prices_include_vat is True
    assert bill.total_eur == Decimal("837.88")
    # 837.88 / 1.19 = 704.0999...
    assert (bill.vat.rate, bill.vat.net_eur, bill.vat.vat_eur) == (
        Decimal("0.19"),
        Decimal("704.10"),
        Decimal("133.78"),
    )


def test_net_prices_add_vat_on_top():
    bill = bill_for(month_readings(2026, 10, energy_wh=1000), prices_include_vat=False)

    # 837.88 x 0.19 = 159.1972
    assert (bill.vat.net_eur, bill.vat.vat_eur) == (Decimal("837.88"), Decimal("159.20"))
    assert bill.total_eur == Decimal("997.08")
