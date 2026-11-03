import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("day_start", sa.Time(), nullable=False),
        sa.Column("day_end", sa.Time(), nullable=False),
        sa.Column("day_ct_per_kwh", sa.String(32), nullable=False),
        sa.Column("night_ct_per_kwh", sa.String(32), nullable=False),
        sa.Column("monthly_fee_eur", sa.String(32), nullable=False),
    )
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("tariff_id", sa.Integer(), sa.ForeignKey("tariffs.id"), nullable=False),
    )
    op.create_table(
        "meters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("meter_number", sa.String(), nullable=False, unique=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
    )
    op.create_table(
        "readings",
        sa.Column("meter_id", sa.Integer(), sa.ForeignKey("meters.id"), primary_key=True),
        sa.Column("interval_start", sa.DateTime(), primary_key=True),
        sa.Column("energy_wh", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("energy_wh >= 0", name="energy_wh_not_negative"),
    )
    op.create_table(
        "reading_corrections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meter_id", sa.Integer(), sa.ForeignKey("meters.id"), nullable=False),
        sa.Column("interval_start", sa.DateTime(), nullable=False),
        sa.Column("energy_wh", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_reading_corrections_meter_interval",
        "reading_corrections",
        ["meter_id", "interval_start"],
    )


def downgrade() -> None:
    op.drop_table("reading_corrections")
    op.drop_table("readings")
    op.drop_table("meters")
    op.drop_table("customers")
    op.drop_table("tariffs")
