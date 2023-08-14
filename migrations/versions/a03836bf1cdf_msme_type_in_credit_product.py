"""msme type in credit product

Revision ID: a03836bf1cdf
Revises: 66aaad70ea76
Create Date: 2023-08-13 13:28:39.255629

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "a03836bf1cdf"
down_revision = "66aaad70ea76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "credit_product",
        sa.Column(
            "borrower_types",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            default="{}",
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("credit_product", "borrower_types")
