"""
add new message type

Revision ID: 867ef39e878c
Revises: 6a60442731bf
Create Date: 2024-10-28 16:29:22.283917

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "867ef39e878c"
down_revision = "6a60442731bf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE message_type ADD VALUE IF NOT EXISTS 'BORROWER_EXTERNAL_ONBOARDING_REMINDER'
      """
        )


def downgrade() -> None:
    pass
