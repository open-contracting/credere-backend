"""change_borrower_uploaded_contracted_at_to_borrower_uploaded_contract_at

Revision ID: 0d937c85609d
Revises: 8ab95d68febd
Create Date: 2023-06-30 14:19:01.544066

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "0d937c85609d"
down_revision = "8ab95d68febd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "application",
        "borrower_uploaded_contracted_at",
        new_column_name="borrower_uploaded_contract_at",
    )


def downgrade() -> None:
    op.alter_column(
        "application",
        "borrower_uploaded_contract_at",
        new_column_name="borrower_uploaded_contracted_at",
    )
