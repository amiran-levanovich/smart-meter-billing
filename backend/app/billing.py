"""Billing core: a month's readings + tariff in, the bill out. No DB, no HTTP."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
INTERVAL = timedelta(minutes=15)
CENT = Decimal("0.01")


@dataclass(frozen=True)
class Tariff:
    day_start: time
    day_end: time
    day_ct_per_kwh: Decimal
    night_ct_per_kwh: Decimal
    monthly_fee_eur: Decimal


@dataclass(frozen=True)
class Reading:
    interval_start: datetime  # aware UTC
    energy_wh: int


@dataclass(frozen=True)
class LineItem:
    kind: str  # "day" | "night" | "fee"
    quantity: Decimal  # kWh, or months for the fee
    unit_price: Decimal  # ct/kWh, or EUR for the fee
    amount_eur: Decimal


@dataclass(frozen=True)
class Notice:
    kind: str  # "dst" | "estimated" | "corrected"
    interval_start: datetime
    energy_wh: int | None = None
    previous_energy_wh: int | None = None
    amount_eur: Decimal | None = None


@dataclass(frozen=True)
class Bill:
    lines: list[LineItem]
    notices: list[Notice]


def to_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def month_intervals(year: int, month: int) -> list[datetime]:
    """UTC starts of every interval in the Berlin calendar month (DST days have 92 or 100)."""
    start = datetime(year, month, 1, tzinfo=BERLIN).astimezone(UTC)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=BERLIN).astimezone(UTC)
    count = (end - start) // INTERVAL
    return [start + i * INTERVAL for i in range(count)]


def is_day(interval_start: datetime, tariff: Tariff) -> bool:
    return tariff.day_start <= interval_start.astimezone(BERLIN).time() < tariff.day_end


def compute_bill(readings: Iterable[Reading], tariff: Tariff, year: int, month: int) -> Bill:
    energy = {r.interval_start: r.energy_wh for r in readings}
    intervals = month_intervals(year, month)
    day_wh = night_wh = 0
    for t in intervals:
        if is_day(t, tariff):
            day_wh += energy[t]
        else:
            night_wh += energy[t]

    def energy_line(kind: str, wh: int, ct_per_kwh: Decimal) -> LineItem:
        kwh = Decimal(wh).scaleb(-3)  # Wh to kWh, exact to 3 places
        return LineItem(kind, kwh, ct_per_kwh, to_cents(kwh * ct_per_kwh / 100))

    return Bill(
        lines=[
            energy_line("day", day_wh, tariff.day_ct_per_kwh),
            energy_line("night", night_wh, tariff.night_ct_per_kwh),
            LineItem("fee", Decimal(1), tariff.monthly_fee_eur, tariff.monthly_fee_eur),
        ],
        notices=clock_changes(intervals),
    )


def clock_changes(intervals: list[datetime]) -> list[Notice]:
    def offset(t: datetime) -> timedelta | None:
        return t.astimezone(BERLIN).utcoffset()

    return [
        Notice("dst", after)
        for before, after in zip(intervals, intervals[1:], strict=False)
        if offset(before) != offset(after)
    ]
