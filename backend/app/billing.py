"""Billing core: a month's readings + tariff in, the bill out. No DB, no HTTP."""

from bisect import bisect_left
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
INTERVAL = timedelta(minutes=15)
CENT = Decimal("0.01")
VAT_RATE = Decimal("0.19")  # electricity is always standard-rated in Germany


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
class Vat:
    rate: Decimal
    net_eur: Decimal
    vat_eur: Decimal


@dataclass(frozen=True)
class Bill:
    lines: list[LineItem]
    total_eur: Decimal
    prices_include_vat: bool
    vat: Vat
    notices: list[Notice]


class NoReadingsError(Exception):
    """The month has no readings at all, so there is nothing to bill."""


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


def compute_bill(
    readings: Iterable[Reading],
    tariff: Tariff,
    year: int,
    month: int,
    prices_include_vat: bool = True,
) -> Bill:
    measured = {r.interval_start: r.energy_wh for r in readings}
    intervals = month_intervals(year, month)
    if not measured.keys() & set(intervals):
        raise NoReadingsError(f"no readings for {year}-{month:02d}")

    times = sorted(measured)
    notices = []
    day_wh = night_wh = 0
    for t in intervals:
        wh = measured.get(t)
        if wh is None:
            wh = estimate(t, times, measured)
            amount = to_cents(cost_ct(wh, t, tariff) / 100)
            notices.append(Notice("estimated", t, wh, amount_eur=amount))
        if is_day(t, tariff):
            day_wh += wh
        else:
            night_wh += wh

    def energy_line(kind: str, wh: int, ct_per_kwh: Decimal) -> LineItem:
        kwh = to_kwh(wh)
        return LineItem(kind, kwh, ct_per_kwh, to_cents(kwh * ct_per_kwh / 100))

    lines = [
        energy_line("day", day_wh, tariff.day_ct_per_kwh),
        energy_line("night", night_wh, tariff.night_ct_per_kwh),
        LineItem("fee", Decimal(1), tariff.monthly_fee_eur, tariff.monthly_fee_eur),
    ]
    lines_sum = sum((item.amount_eur for item in lines), Decimal(0))
    if prices_include_vat:
        net = to_cents(lines_sum / (1 + VAT_RATE))
        vat = Vat(VAT_RATE, net, lines_sum - net)
    else:
        vat = Vat(VAT_RATE, lines_sum, to_cents(lines_sum * VAT_RATE))

    return Bill(
        lines=lines,
        total_eur=vat.net_eur + vat.vat_eur,
        prices_include_vat=prices_include_vat,
        vat=vat,
        notices=clock_changes(intervals) + notices,
    )


def to_kwh(wh: int) -> Decimal:
    return Decimal(wh).scaleb(-3)  # exact to 3 places


def price_ct(interval_start: datetime, tariff: Tariff) -> Decimal:
    return tariff.day_ct_per_kwh if is_day(interval_start, tariff) else tariff.night_ct_per_kwh


def cost_ct(wh: int, interval_start: datetime, tariff: Tariff) -> Decimal:
    return to_kwh(wh) * price_ct(interval_start, tariff)


def estimate(t: datetime, times: list[datetime], measured: dict[datetime, int]) -> int:
    """Linear interpolation between the nearest real readings around t, to whole Wh.
    With a reading on one side only, copy it. `times` is sorted(measured)."""
    i = bisect_left(times, t)
    before = times[i - 1] if i > 0 else None
    after = times[i] if i < len(times) else None
    if before is None or after is None:
        return measured[before or after]
    share = Decimal((t - before) / INTERVAL) / Decimal((after - before) / INTERVAL)
    value = measured[before] + (measured[after] - measured[before]) * share
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def clock_changes(intervals: list[datetime]) -> list[Notice]:
    def offset(t: datetime) -> timedelta | None:
        return t.astimezone(BERLIN).utcoffset()

    return [
        Notice("dst", after)
        for before, after in zip(intervals, intervals[1:], strict=False)
        if offset(before) != offset(after)
    ]
