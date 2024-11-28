"""
add new action type

Revision ID: f4f2b2a76181
Revises: 867ef39e878c
Create Date: 2024-11-28 11:55:31.469382

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f4f2b2a76181"
down_revision = "867ef39e878c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'FI_LAPSE_APPLICATION'
        """
        )


def downgrade() -> None:
    pass
