"""Add lender_rejected_at column to applications table

Revision ID: bfd66392691e
Revises: 2ca870aa737d
Create Date: 2023-06-19 10:25:49.276634

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bfd66392691e"
down_revision = "2ca870aa737d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application",
        sa.Column("lender_rejected_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column(
        "application",
        "borrewed_uploaded_contracted_at",
        new_column_name="borrower_uploaded_contracted_at",
    )


def downgrade() -> None:
    op.alter_column(
        "application",
        "borrower_uploaded_contracted_at",
        new_column_name="borrowed_uploaded_contracted_at",
    )
    op.drop_column("application", "lender_rejected_at")
