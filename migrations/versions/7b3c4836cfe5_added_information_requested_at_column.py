"""Added information_requested_at column

Revision ID: 7b3c4836cfe5
Revises: 9fee2d77e941
Create Date: 2023-06-21 13:44:30.608781

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7b3c4836cfe5"
down_revision = "9fee2d77e941"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application",
        sa.Column(
            "information_requested_at", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("application", "information_requested_at")
