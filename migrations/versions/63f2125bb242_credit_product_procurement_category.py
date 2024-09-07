"""credit product procurement category

Revision ID: 63f2125bb242
Revises: 6a0d845e53cb
Create Date: 2024-07-03 17:19:57.192737

"""

import sqlalchemy as sa
import sqlmodel  # added
from alembic import op

# revision identifiers, used by Alembic.
revision = "63f2125bb242"
down_revision = "6a0d845e53cb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "credit_product",
        sa.Column(
            "procurement_category_to_exclude",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("credit_product", "procurement_category_to_exclude")
