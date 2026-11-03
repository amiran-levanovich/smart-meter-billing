import uuid
from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Time, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime, Uuid

from app.billing import Tariff


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"naive datetime {value} cannot be stored as UTC")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        return None if value is None else value.replace(tzinfo=UTC)


class DecimalText(TypeDecorator[Decimal]):
    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect) -> str | None:
        return None if value is None else str(value)

    def process_result_value(self, value: str | None, dialect) -> Decimal | None:
        return None if value is None else Decimal(value)


class Base(DeclarativeBase):
    pass


class TariffRecord(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    day_start: Mapped[time] = mapped_column(Time)
    day_end: Mapped[time] = mapped_column(Time)
    day_ct_per_kwh: Mapped[Decimal] = mapped_column(DecimalText)
    night_ct_per_kwh: Mapped[Decimal] = mapped_column(DecimalText)
    monthly_fee_eur: Mapped[Decimal] = mapped_column(DecimalText)

    def to_tariff(self) -> Tariff:
        return Tariff(
            self.day_start,
            self.day_end,
            self.day_ct_per_kwh,
            self.night_ct_per_kwh,
            self.monthly_fee_eur,
        )


class CustomerRecord(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))

    tariff: Mapped[TariffRecord] = relationship()
    meters: Mapped[list["MeterRecord"]] = relationship(back_populates="customer")


class MeterRecord(Base):
    __tablename__ = "meters"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True)
    meter_number: Mapped[str] = mapped_column(unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))

    customer: Mapped[CustomerRecord] = relationship(back_populates="meters")


class ReadingRecord(Base):
    __tablename__ = "readings"
    __table_args__ = (CheckConstraint("energy_wh >= 0", name="energy_wh_not_negative"),)

    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"), primary_key=True)
    interval_start: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)
    energy_wh: Mapped[int]
    received_at: Mapped[datetime] = mapped_column(UTCDateTime)


class ReplacedReadingRecord(Base):
    __tablename__ = "replaced_readings"
    __table_args__ = (Index("ix_replaced_readings_meter_interval", "meter_id", "interval_start"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meter_id: Mapped[int] = mapped_column(ForeignKey("meters.id"))
    interval_start: Mapped[datetime] = mapped_column(UTCDateTime)
    energy_wh: Mapped[int]
    received_at: Mapped[datetime] = mapped_column(UTCDateTime)
    superseded_at: Mapped[datetime] = mapped_column(UTCDateTime)
