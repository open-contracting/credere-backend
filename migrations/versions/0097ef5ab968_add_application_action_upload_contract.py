"""
add application action upload contract

Revision ID: 0097ef5ab968
Revises: 7e81b8a695ed
Create Date: 2023-07-07 12:38:08.011391

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0097ef5ab968"
down_revision = "7e81b8a695ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'MSME_UPLOAD_CONTRACT'
        """
        )


def downgrade() -> None:
    pass
