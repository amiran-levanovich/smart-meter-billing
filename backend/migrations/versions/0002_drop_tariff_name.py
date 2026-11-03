import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tariffs") as batch:
        batch.drop_column("name")


def downgrade() -> None:
    with op.batch_alter_table("tariffs") as batch:
        batch.add_column(sa.Column("name", sa.String(), nullable=False, server_default=""))
