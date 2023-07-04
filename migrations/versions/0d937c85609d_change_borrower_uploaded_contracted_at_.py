"""change_borrower_uploaded_contracted_at_to_borrower_uploaded_contract_at

Revision ID: 0d937c85609d
Revises: 8ab95d68febd
Create Date: 2023-06-30 14:19:01.544066

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0d937c85609d"
down_revision = "8ab95d68febd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("lender")

    column_info = None
    for column in columns:
        if column["name"] == "borrower_uploaded_contracted_at":
            column_info = column["name"]
            break

    if column_info is not None:
        op.alter_column(
            "application",
            "borrower_uploaded_contracted_at",
            new_column_name="borrower_uploaded_contract_at",
        )

    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'BORROWER_UPLOADED_CONTRACT'
        """
        )


def downgrade() -> None:
    op.alter_column(
        "application",
        "borrower_uploaded_contract_at",
        new_column_name="borrower_uploaded_contracted_at",
    )
