"""user notification preferences

Revision ID: 1fa1da5eb109
Revises: 755091b6b4b4
Create Date: 2024-08-24 14:10:07.389323

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "1fa1da5eb109"
down_revision = "755091b6b4b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "credere_user",
        sa.Column(
            "notification_preferences",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )


def downgrade() -> None:
    op.drop_column("credere_user", "notification_preferences")
