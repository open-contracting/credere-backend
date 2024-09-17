"""
add OCP_DOWNLOADED_APPLICATION to application_action_type

Revision ID: 66aaad70ea76
Revises: 637b31a11d96
Create Date: 2023-08-03 17:40:03.683540

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "66aaad70ea76"
down_revision = "637b31a11d96"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'OCP_DOWNLOAD_APPLICATION'
        """
        )


def downgrade() -> None:
    # enums cannot be downgraded
    pass
