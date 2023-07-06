"""repayment application data

Revision ID: 9df7f1e04a80
Revises: cb18946fe90f
Create Date: 2023-07-03 02:20:02.375632

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9df7f1e04a80"
down_revision = "cb18946fe90f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application", sa.Column("payment_start_date", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "application", sa.Column("repayment_years", sa.Integer(), nullable=True)
    )
    op.add_column(
        "application",
        sa.Column("borrower_credit_product_selected_at", sa.DateTime(), nullable=True),
    )
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'APPLICATION_CALCULATOR_DATA_UPDATE'
        """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'APPLICATION_CONFIRM_CREDIT_PRODUCT'
        """
        )


def downgrade() -> None:
    op.drop_column("application", "repayment_years")
    op.drop_column("application", "payment_start_date")
    op.drop_column("application", "borrower_credit_product_selected_at")
