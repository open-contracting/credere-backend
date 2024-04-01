"""add application completed at

Revision ID: d5aff8922d09
Revises: 0097ef5ab968
Create Date: 2023-07-07 14:01:15.566981

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d5aff8922d09"
down_revision = "0097ef5ab968"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application",
        sa.Column("lender_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application", "lender_completed_at")
