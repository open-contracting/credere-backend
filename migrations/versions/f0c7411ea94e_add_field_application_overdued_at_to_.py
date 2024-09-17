"""
add field application overdued at to applications

Revision ID: f0c7411ea94e
Revises: d5aff8922d09
Create Date: 2023-07-10 12:02:37.561635

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f0c7411ea94e"
down_revision = "d5aff8922d09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application",
        sa.Column("overdued_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application", "overdued_at")
