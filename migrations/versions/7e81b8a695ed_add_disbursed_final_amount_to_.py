"""add_disbursed_final_amount_to_application

Revision ID: 7e81b8a695ed
Revises: 8ab95d68febd
Create Date: 2023-07-05 12:03:03.203946

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7e81b8a695ed"
down_revision = "8ab95d68febd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application",
        sa.Column(
            "disbursed_final_amount", sa.DECIMAL(precision=16, scale=2), nullable=True
        ),
    )
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'FI_COMPLETE_APPLICATION'
        """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'FI_START_APPLICATION'
        """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'FI_REQUEST_INFORMATION'
        """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED'
        """
        )


def downgrade() -> None:
    op.drop_column("application", "disbursed_final_amount")
