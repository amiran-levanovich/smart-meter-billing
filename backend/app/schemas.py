from datetime import UTC, date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.billing import BERLIN, Bill, Reading


class Period(BaseModel):
    month: str
    start: datetime
    end: datetime


UNITS: dict[str, tuple[Literal["kWh", "month"], Literal["ct/kWh", "EUR"]]] = {
    "day": ("kWh", "ct/kWh"),
    "night": ("kWh", "ct/kWh"),
    "fee": ("month", "EUR"),
}


class LineItemOut(BaseModel):
    kind: Literal["day", "night", "fee"]
    quantity: Decimal
    unit: Literal["kWh", "month"]
    unit_price: Decimal
    unit_price_unit: Literal["ct/kWh", "EUR"]
    amount_eur: Decimal


class VatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rate: Decimal
    net_eur: Decimal
    vat_eur: Decimal


class DailyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    day_kwh: Decimal
    night_kwh: Decimal
    day_eur: Decimal
    night_eur: Decimal


class NoticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: Literal["dst", "estimated", "corrected"]
    interval_start: datetime
    energy_wh: int | None
    previous_energy_wh: int | None
    amount_eur: Decimal | None
    clock: Literal["back", "forward"] | None

    @field_validator("interval_start")
    @classmethod
    def in_berlin(cls, interval_start: datetime) -> datetime:
        return interval_start.astimezone(BERLIN)


class BillOut(BaseModel):
    period: Period
    customer_name: str
    meter_number: str
    lines: list[LineItemOut]
    total_eur: Decimal
    prices_include_vat: bool
    vat: VatOut
    night_share_percent: Decimal
    night_saving_eur: Decimal
    daily: list[DailyOut]
    notices: list[NoticeOut]
    measured_intervals: int
    unbilled_intervals: int
    day_start: time
    day_end: time


def bill_out(bill: Bill, month: str, customer_name: str, meter_number: str) -> BillOut:
    return BillOut(
        period=Period(month=month, start=bill.period_start, end=bill.period_end),
        customer_name=customer_name,
        meter_number=meter_number,
        lines=[
            LineItemOut(
                kind=item.kind,
                quantity=item.quantity,
                unit=UNITS[item.kind][0],
                unit_price=item.unit_price,
                unit_price_unit=UNITS[item.kind][1],
                amount_eur=item.amount_eur,
            )
            for item in bill.lines
        ],
        total_eur=bill.total_eur,
        prices_include_vat=bill.prices_include_vat,
        vat=VatOut.model_validate(bill.vat),
        night_share_percent=bill.night_share_percent,
        night_saving_eur=bill.night_saving_eur,
        daily=[DailyOut.model_validate(d) for d in bill.daily],
        notices=[NoticeOut.model_validate(n) for n in bill.notices],
        measured_intervals=bill.measured_intervals,
        unbilled_intervals=bill.unbilled_intervals,
        day_start=bill.day_start,
        day_end=bill.day_end,
    )


class ReadingIn(BaseModel):
    timestamp: AwareDatetime
    energy_wh: int = Field(strict=True, ge=0, le=1_000_000)

    @field_validator("timestamp")
    @classmethod
    def on_quarter_hour(cls, timestamp: datetime) -> datetime:
        utc = timestamp.astimezone(UTC)
        if utc.minute % 15 or utc.second or utc.microsecond:
            raise ValueError("timestamp must start a 15-minute interval")
        return utc

    def to_reading(self) -> Reading:
        return Reading(self.timestamp, self.energy_wh)


class MonthsOut(BaseModel):
    first: str
    last: str
