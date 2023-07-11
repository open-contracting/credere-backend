"""add keys to application action enum

Revision ID: 9455718e2178
Revises: d5aff8922d09
Create Date: 2023-07-11 10:21:57.021119

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "9455718e2178"
down_revision = "d5aff8922d09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("application_award_borrower_identifier_key", "application")
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'COPIED_APPLICATION'
      """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'APPLICATION_COPIED_FROM'
      """
        )


def downgrade() -> None:
    op.create_unique_constraint(
        "application_award_borrower_identifier_key",
        "application",
        ["award_borrower_identifier"],
    )
