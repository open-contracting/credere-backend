"""added message.lenderId enum.AWAITING_INFORMATION

Revision ID: 173969eb685c
Revises: 7b3c4836cfe5
Create Date: 2023-06-27 10:24:01.195618

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "173969eb685c"
down_revision = "7b3c4836cfe5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("message", sa.Column("lender_id", sa.Integer(), nullable=True))
    op.create_foreign_key(None, "message", "lender", ["lender_id"], ["id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    op.drop_column("message", "lender_id")
    # ### end Alembic commands ###
