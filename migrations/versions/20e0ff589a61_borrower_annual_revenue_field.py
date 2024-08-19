"""borrower annual_revenue field

Revision ID: 20e0ff589a61
Revises: 8a775f48bf88
Create Date: 2024-08-17 11:27:20.097269

"""

from alembic import op
import sqlalchemy as sa
import sqlmodel  # added

# revision identifiers, used by Alembic.
revision = "20e0ff589a61"
down_revision = "8a775f48bf88"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("borrower", sa.Column("annual_revenue", sa.DECIMAL(precision=16, scale=2), nullable=True))
    op.add_column("borrower", sa.Column("currency", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.execute("UPDATE borrower set currency = ''")


def downgrade() -> None:
    op.drop_column("borrower", "currency")
    op.drop_column("borrower", "annual_revenue")
