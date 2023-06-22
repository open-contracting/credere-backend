"""Added application_lapsed_at column

Revision ID: 0f474dd039b4
Revises: 7b3c4836cfe5
Create Date: 2023-06-22 11:55:22.835909

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0f474dd039b4"
down_revision = "7b3c4836cfe5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application",
        sa.Column("application_lapsed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application", "application_lapsed_at")
