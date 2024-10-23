"""
add external onboarding track logic

Revision ID: 6a60442731bf
Revises: 8cc5c33573f4
Create Date: 2024-10-23 13:35:39.181958

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6a60442731bf"
down_revision = "8cc5c33573f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application", sa.Column("borrower_accessed_external_onboarding_at", sa.DateTime(timezone=True), nullable=True)
    )

    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'MSME_ACCESSED_EXTERNAL_ONBOARDING'
      """
        )


def downgrade() -> None:
    op.drop_column("application", "borrower_accessed_external_onboarding_at")
