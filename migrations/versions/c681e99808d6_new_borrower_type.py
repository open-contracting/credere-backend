"""new borrower type

Revision ID: c681e99808d6
Revises: 6a0d845e53cb
Create Date: 2024-07-02 11:41:44.999644

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c681e99808d6"
down_revision = "6a0d845e53cb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE borrower_size ADD VALUE IF NOT EXISTS 'BIG'
      """
        )


def downgrade() -> None:
    pass
