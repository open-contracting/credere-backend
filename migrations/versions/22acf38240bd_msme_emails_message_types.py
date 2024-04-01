"""msme emails message types

Revision ID: 22acf38240bd
Revises: a03836bf1cdf
Create Date: 2023-09-04 08:49:47.084554

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "22acf38240bd"
down_revision = "a03836bf1cdf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE message_type ADD VALUE IF NOT EXISTS 'CREDIT_DISBURSED'
      """
        )


def downgrade() -> None:
    pass
