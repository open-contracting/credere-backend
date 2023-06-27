"""added message.lenderId enum.AWAITING_INFORMATION

Revision ID: 173969eb685c
Revises: df236486f60a
Create Date: 2023-06-27 10:24:01.195618

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "173969eb685c"
down_revision = "df236486f60a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("message", sa.Column("lender_id", sa.Integer(), nullable=True))
    op.create_foreign_key(None, "message", "lender", ["lender_id"], ["id"])
    # Add new ENUM value
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE message_type ADD VALUE IF NOT EXISTS 'AWAITING_INFORMATION'
        """
        )
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column("message", "lender_id")
    # Downgrading ENUM is not directly possible in PostgreSQL
    # ### end Alembic commands ###
