from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.billing import BERLIN, Bill


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
    rate: Decimal
    net_eur: Decimal
    vat_eur: Decimal


class DailyOut(BaseModel):
    date: date
    day_kwh: Decimal
    night_kwh: Decimal
    day_eur: Decimal
    night_eur: Decimal


class NoticeOut(BaseModel):
    kind: Literal["dst", "estimated", "corrected"]
    interval_start: datetime
    energy_wh: int | None
    previous_energy_wh: int | None
    amount_eur: Decimal | None


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
        vat=VatOut(rate=bill.vat.rate, net_eur=bill.vat.net_eur, vat_eur=bill.vat.vat_eur),
        night_share_percent=bill.night_share_percent,
        night_saving_eur=bill.night_saving_eur,
        daily=[
            DailyOut(
                date=d.date,
                day_kwh=d.day_kwh,
                night_kwh=d.night_kwh,
                day_eur=d.day_eur,
                night_eur=d.night_eur,
            )
            for d in bill.daily
        ],
        notices=[
            NoticeOut(
                kind=n.kind,
                interval_start=n.interval_start.astimezone(BERLIN),
                energy_wh=n.energy_wh,
                previous_energy_wh=n.previous_energy_wh,
                amount_eur=n.amount_eur,
            )
            for n in bill.notices
        ],
    )
