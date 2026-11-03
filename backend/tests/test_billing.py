from dataclasses import replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app.billing import InvalidTariffError, Reading, Tariff, compute_bill

BERLIN = ZoneInfo("Europe/Berlin")
TARIFF = Tariff(
    day_start=time(6, 0),
    day_end=time(22, 0),
    day_ct_per_kwh=Decimal("31.847"),
    night_ct_per_kwh=Decimal("19.392"),
    monthly_fee_eur=Decimal("12.90"),
)


def month_readings(year: int, month: int, energy_wh: int = 0) -> dict[datetime, int]:
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


def estimates(bill) -> list[tuple[datetime, int]]:
    return [(n.interval_start, n.energy_wh) for n in bill.notices if n.kind == "estimated"]


def test_missing_interval_is_estimated_from_its_neighbours():
    readings = month_readings(2026, 10)
    readings[berlin(2026, 10, 13, 14, 15)] = 2460
    readings[berlin(2026, 10, 13, 14, 45)] = 2115
    del readings[berlin(2026, 10, 13, 14, 30)]

    bill = bill_for(readings)

    # (2460 + 2115) / 2 = 2287.5, rounded half-up to whole Wh
    assert line(bill, "day").quantity == Decimal("6.863")
    [notice] = [n for n in bill.notices if n.kind == "estimated"]
    assert notice.interval_start == berlin(2026, 10, 13, 14, 30)
    assert notice.energy_wh == 2288
    # 2.288 kWh x 31.847 ct = 72.86 ct
    assert notice.amount_eur == Decimal("0.73")


def test_estimate_rounds_half_a_watt_hour_up():
    readings = month_readings(2026, 10)
    readings[berlin(2026, 10, 2, 9, 0)] = 1000
    readings[berlin(2026, 10, 2, 9, 30)] = 1001
    del readings[berlin(2026, 10, 2, 9, 15)]

    assert estimates(bill_for(readings)) == [(berlin(2026, 10, 2, 9, 15), 1001)]


def test_gap_run_is_interpolated_linearly_between_real_readings():
    readings = month_readings(2026, 10)
    readings[berlin(2026, 10, 2, 9, 0)] = 1000
    readings[berlin(2026, 10, 2, 9, 45)] = 2000
    del readings[berlin(2026, 10, 2, 9, 15)]
    del readings[berlin(2026, 10, 2, 9, 30)]

    assert estimates(bill_for(readings)) == [
        (berlin(2026, 10, 2, 9, 15), 1333),
        (berlin(2026, 10, 2, 9, 30), 1667),
    ]


def test_gap_of_one_hour_is_still_interpolated():
    readings = month_readings(2026, 10)
    readings[berlin(2026, 10, 2, 9, 0)] = 500
    readings[berlin(2026, 10, 2, 10, 15)] = 1000
    for minute in (15, 30, 45, 60):
        del readings[berlin(2026, 10, 2, 9, 0) + timedelta(minutes=minute)]

    assert [wh for _, wh in estimates(bill_for(readings))] == [600, 700, 800, 900]


def test_gap_longer_than_one_hour_is_not_billed():
    readings = month_readings(2026, 10)
    readings[berlin(2026, 10, 2, 9, 0)] = 500
    readings[berlin(2026, 10, 2, 10, 30)] = 1000
    for minute in (15, 30, 45, 60, 75):
        del readings[berlin(2026, 10, 2, 9, 0) + timedelta(minutes=minute)]

    bill = bill_for(readings)

    assert estimates(bill) == []
    assert line(bill, "day").quantity == Decimal("1.500")


def test_gap_at_month_start_uses_the_reading_before_the_month():
    readings = month_readings(2026, 10)
    del readings[berlin(2026, 10, 1, 0, 0)]
    readings[berlin(2026, 10, 1, 0, 15)] = 600
    readings[berlin(2026, 9, 30, 23, 45)] = 400

    bill = bill_for(readings)

    assert estimates(bill) == [(berlin(2026, 10, 1, 0, 0), 500)]
    assert line(bill, "night").quantity == Decimal("1.100")


def test_gap_at_month_end_without_a_later_reading_is_not_billed():
    readings = month_readings(2026, 10)
    readings[berlin(2026, 10, 31, 23, 30)] = 700
    del readings[berlin(2026, 10, 31, 23, 45)]

    bill = bill_for(readings)

    assert estimates(bill) == []
    assert line(bill, "night").quantity == Decimal("0.700")


def test_intervals_after_the_last_reading_are_not_billed():
    bill = bill_for({berlin(2026, 11, 2, 10, 0): 1000}, month=11)

    assert estimates(bill) == []
    assert [(item.kind, item.quantity) for item in bill.lines] == [
        ("day", Decimal("1.000")),
        ("night", Decimal("0.000")),
        ("fee", Decimal("1")),
    ]
    assert len(bill.daily) == 30


def test_month_without_readings_bills_only_the_fee():
    bill = bill_for({berlin(2026, 10, 31, 23, 45): 400}, month=11)

    assert bill.total_eur == Decimal("12.90")
    assert bill.notices == []


def test_corrected_reading_is_billed_at_its_latest_value_with_a_notice():
    readings = [Reading(t, 0) for t in month_readings(2026, 10)]
    corrected_at = berlin(2026, 10, 8, 10, 15)
    readings = [r for r in readings if r.interval_start != corrected_at]
    readings.append(Reading(corrected_at, 3200, previous_energy_wh=2419))

    bill = compute_bill(readings, TARIFF, 2026, 10)

    assert line(bill, "day").quantity == Decimal("3.200")
    corrected = [n for n in bill.notices if n.kind == "corrected"]
    assert [(n.interval_start, n.energy_wh, n.previous_energy_wh) for n in corrected] == [
        (corrected_at, 3200, 2419)
    ]


def test_notices_are_in_chronological_order():
    readings = month_readings(2026, 10)
    del readings[berlin(2026, 10, 13, 14, 30)]
    corrected_at = berlin(2026, 10, 8, 10, 15)
    del readings[corrected_at]
    bill = compute_bill(
        [Reading(t, wh) for t, wh in readings.items()]
        + [Reading(corrected_at, 3200, previous_energy_wh=2419)],
        TARIFF,
        2026,
        10,
    )

    assert [n.kind for n in bill.notices] == ["corrected", "estimated", "dst"]


def test_period_runs_from_local_midnight_to_local_midnight():
    bill = bill_for(month_readings(2026, 10))

    assert (bill.period_start, bill.period_end) == (
        datetime.fromisoformat("2026-10-01T00:00:00+02:00"),
        datetime.fromisoformat("2026-11-01T00:00:00+01:00"),
    )


def test_night_share_is_night_kwh_over_total_kwh_in_whole_percent():
    bill = bill_for(month_readings(2026, 10, energy_wh=1000))

    # 996 / 2980 = 33.42 %
    assert bill.night_share_percent == Decimal("33")


def test_night_saving_is_night_kwh_times_the_day_night_price_gap():
    bill = bill_for(month_readings(2026, 10, energy_wh=1000))

    # 996 kWh x (31.847 - 19.392) ct = 124.0518 EUR
    assert bill.night_saving_eur == Decimal("124.05")


def test_daily_figures_split_day_and_night_per_berlin_date():
    bill = bill_for(month_readings(2026, 10, energy_wh=1000))

    assert len(bill.daily) == 31
    by_date = {d.date: d for d in bill.daily}
    first = by_date[date(2026, 10, 1)]
    # 64 kWh x 31.847 ct = 20.38208; 32 kWh x 19.392 ct = 6.20544
    assert (first.date, first.day_kwh, first.night_kwh, first.day_eur, first.night_eur) == (
        date(2026, 10, 1),
        Decimal("64.000"),
        Decimal("32.000"),
        Decimal("20.38"),
        Decimal("6.21"),
    )
    assert by_date[date(2026, 10, 25)].night_kwh == Decimal("36.000")


def test_month_with_zero_consumption_has_no_night_share():
    assert bill_for(month_readings(2026, 10)).night_share_percent == Decimal("0")


def test_december_bill_ends_at_new_year_midnight():
    bill = bill_for(month_readings(2026, 12, energy_wh=1000), year=2026, month=12)

    assert bill.period_end == datetime.fromisoformat("2027-01-01T00:00:00+01:00")
    # 31 days x 64 day intervals, 31 x 32 night intervals
    assert line(bill, "day").quantity == Decimal("1984.000")
    assert line(bill, "night").quantity == Decimal("992.000")


def test_correction_outside_the_month_is_not_a_notice():
    readings = [Reading(t, 0) for t in month_readings(2026, 10)]
    readings.append(Reading(berlin(2026, 9, 30, 23, 45), 500, previous_energy_wh=400))

    bill = compute_bill(readings, TARIFF, 2026, 10)

    assert [n for n in bill.notices if n.kind == "corrected"] == []


def test_day_window_off_the_15_minute_grid_is_rejected():
    with pytest.raises(InvalidTariffError):
        compute_bill([], replace(TARIFF, day_start=time(6, 10)), 2026, 10)
