from bisect import bisect_left
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")
INTERVAL = timedelta(minutes=15)
MAX_ESTIMATED_GAP = 4
CENT = Decimal("0.01")
VAT_RATE = Decimal("0.19")

Rate = Literal["day", "night"]


@dataclass(frozen=True)
class Tariff:
    day_start: time
    day_end: time
    day_ct_per_kwh: Decimal
    night_ct_per_kwh: Decimal
    monthly_fee_eur: Decimal


@dataclass(frozen=True)
class Reading:
    interval_start: datetime
    energy_wh: int
    previous_energy_wh: int | None = None


@dataclass(frozen=True)
class LineItem:
    kind: Literal["day", "night", "fee"]
    quantity: Decimal
    unit_price: Decimal
    amount_eur: Decimal


@dataclass(frozen=True)
class Notice:
    kind: Literal["dst", "estimated", "corrected"]
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
class DailyUsage:
    date: date
    day_kwh: Decimal
    night_kwh: Decimal
    day_eur: Decimal
    night_eur: Decimal


@dataclass(frozen=True)
class Bill:
    period_start: datetime
    period_end: datetime
    lines: list[LineItem]
    total_eur: Decimal
    prices_include_vat: bool
    vat: Vat
    night_share_percent: Decimal
    night_saving_eur: Decimal
    daily: list[DailyUsage]
    notices: list[Notice]


class InvalidTariffError(ValueError):
    pass


def to_cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def to_kwh(wh: int) -> Decimal:
    return Decimal(wh).scaleb(-3)


def eur(kwh: Decimal, ct_per_kwh: Decimal) -> Decimal:
    return to_cents(kwh * ct_per_kwh / 100)


def month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=BERLIN).astimezone(UTC)
    end = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=BERLIN).astimezone(UTC)
    return start, end


def month_intervals(year: int, month: int) -> list[datetime]:
    start, end = month_bounds(year, month)
    count = (end - start) // INTERVAL
    return [start + i * INTERVAL for i in range(count)]


def rate_of(interval_start: datetime, tariff: Tariff) -> Rate:
    in_window = tariff.day_start <= interval_start.astimezone(BERLIN).time() < tariff.day_end
    return "day" if in_window else "night"


def compute_bill(
    readings: Iterable[Reading],
    tariff: Tariff,
    year: int,
    month: int,
    prices_include_vat: bool = True,
) -> Bill:
    for edge in (tariff.day_start, tariff.day_end):
        if edge.minute % 15 or edge.second or edge.microsecond:
            raise InvalidTariffError(f"day window edge {edge} is not on a 15-minute mark")
    price: dict[Rate, Decimal] = {"day": tariff.day_ct_per_kwh, "night": tariff.night_ct_per_kwh}
    readings = list(readings)
    measured = {r.interval_start: r.energy_wh for r in readings}
    intervals = month_intervals(year, month)
    in_month = set(intervals)

    times = sorted(measured)
    notices = clock_changes(intervals) + [
        Notice("corrected", r.interval_start, r.energy_wh, r.previous_energy_wh)
        for r in readings
        if r.previous_energy_wh is not None and r.interval_start in in_month
    ]
    per_date: defaultdict[date, dict[Rate, int]] = defaultdict(lambda: {"day": 0, "night": 0})
    for t in intervals:
        rate = rate_of(t, tariff)
        totals = per_date[t.astimezone(BERLIN).date()]
        wh = measured.get(t)
        if wh is None:
            wh = estimate(t, times, measured)
            if wh is None:
                continue
            notices.append(Notice("estimated", t, wh, amount_eur=eur(to_kwh(wh), price[rate])))
        totals[rate] += wh
    day_wh = sum(wh["day"] for wh in per_date.values())
    night_wh = sum(wh["night"] for wh in per_date.values())

    lines = [
        LineItem("day", to_kwh(day_wh), price["day"], eur(to_kwh(day_wh), price["day"])),
        LineItem("night", to_kwh(night_wh), price["night"], eur(to_kwh(night_wh), price["night"])),
        LineItem("fee", Decimal(1), tariff.monthly_fee_eur, tariff.monthly_fee_eur),
    ]
    lines_sum = sum((item.amount_eur for item in lines), Decimal(0))
    if prices_include_vat:
        net = to_cents(lines_sum / (1 + VAT_RATE))
        vat = Vat(VAT_RATE, net, lines_sum - net)
    else:
        vat = Vat(VAT_RATE, lines_sum, to_cents(lines_sum * VAT_RATE))

    return Bill(
        period_start=intervals[0].astimezone(BERLIN),
        period_end=(intervals[-1] + INTERVAL).astimezone(BERLIN),
        lines=lines,
        total_eur=vat.net_eur + vat.vat_eur,
        prices_include_vat=prices_include_vat,
        vat=vat,
        night_share_percent=night_share_percent(day_wh, night_wh),
        night_saving_eur=eur(to_kwh(night_wh), price["day"] - price["night"]),
        daily=[
            DailyUsage(
                local_date,
                to_kwh(wh["day"]),
                to_kwh(wh["night"]),
                eur(to_kwh(wh["day"]), price["day"]),
                eur(to_kwh(wh["night"]), price["night"]),
            )
            for local_date, wh in per_date.items()
        ],
        notices=sorted(notices, key=lambda n: n.interval_start),
    )


def night_share_percent(day_wh: int, night_wh: int) -> Decimal:
    if day_wh + night_wh == 0:
        return Decimal(0)
    share = Decimal(100) * night_wh / (day_wh + night_wh)
    return share.quantize(Decimal(1), rounding=ROUND_HALF_UP)


def estimate(t: datetime, times: list[datetime], measured: dict[datetime, int]) -> int | None:
    i = bisect_left(times, t)
    before = times[i - 1] if i > 0 else None
    after = times[i] if i < len(times) else None
    if before is None or after is None or after - before > (MAX_ESTIMATED_GAP + 1) * INTERVAL:
        return None
    share = Decimal((t - before) // INTERVAL) / Decimal((after - before) // INTERVAL)
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
