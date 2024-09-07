"""new application actions

Revision ID: e4389132baa5
Revises: fe69372ecf30
Create Date: 2024-03-04 17:48:20.641103

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e4389132baa5"
down_revision = "fe69372ecf30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'APPLICATION_ROLLBACK_SELECT_PRODUCT';
        """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT'
        """
        )


def downgrade() -> None:
    pass
