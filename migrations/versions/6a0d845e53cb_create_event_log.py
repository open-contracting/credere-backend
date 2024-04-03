"""create event log

Revision ID: 6a0d845e53cb
Revises: e4389132baa5
Create Date: 2024-04-03 09:18:14.453005

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel  # added
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "6a0d845e53cb"
down_revision = "e4389132baa5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("message", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("traceback", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("event_log")
