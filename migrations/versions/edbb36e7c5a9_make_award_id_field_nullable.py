"""Make award_id field nullable

Revision ID: edbb36e7c5a9
Revises: bfd66392691e
Create Date: 2023-06-21 09:13:52.118045

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "edbb36e7c5a9"
down_revision = "bfd66392691e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("application")

    column_info = None
    for column in columns:
        if column["name"] == "award_id":
            column_info = column
            break

    if column_info is not None:
        if column_info["nullable"]:
            # The award_id column is already nullable, no migration required
            return

    # The award_id column is not nullable or doesn't exist, perform the migration
    op.alter_column(
        "application",
        "award_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("application")

    column_info = None
    for column in columns:
        if column["name"] == "award_id":
            column_info = column
            break

    if column_info is not None:
        if not column_info["nullable"]:
            # The award_id column is not nullable, perform the downgrade
            op.alter_column(
                "application",
                "award_id",
                existing_type=sa.Integer(),
                nullable=False,
            )
