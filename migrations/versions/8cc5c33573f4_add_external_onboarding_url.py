"""
add external onboarding url

Revision ID: 8cc5c33573f4
Revises: 59cf8dc3cfde
Create Date: 2024-10-17 13:24:01.833206

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision = "8cc5c33573f4"
down_revision = "59cf8dc3cfde"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lender",
        sa.Column(
            "external_onboarding_url",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
            server_default="",
        ),
    )
    op.drop_column("lender", "default_pre_approval_message")
    # ### end Alembic commands ###


def downgrade() -> None:
    op.add_column(
        "lender", sa.Column("default_pre_approval_message", sa.VARCHAR(), autoincrement=False, nullable=False)
    )
    op.drop_column("lender", "external_onboarding_url")
