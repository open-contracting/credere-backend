"""
lender default message

Revision ID: 1d633984e7c1
Revises: 63f2125bb242
Create Date: 2024-07-08 14:41:07.483650

"""

import sqlalchemy as sa
import sqlmodel  # added
from alembic import op

# revision identifiers, used by Alembic.
revision = "1d633984e7c1"
down_revision = "63f2125bb242"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lender",
        sa.Column(
            "default_pre_approval_message",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("lender", "default_pre_approval_message")
