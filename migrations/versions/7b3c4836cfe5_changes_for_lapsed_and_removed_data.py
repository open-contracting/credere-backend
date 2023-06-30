"""Added information_requested_at column

Revision ID: 7b3c4836cfe5
Revises: df236486f60a
Create Date: 2023-06-21 13:44:30.608781

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7b3c4836cfe5"
down_revision = "df236486f60a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "application",
        sa.Column(
            "information_requested_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "application",
        sa.Column("application_lapsed_at", sa.DateTime(timezone=True), nullable=True),
    )
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
    op.drop_column("application", "information_requested_at")
    op.drop_column("application", "application_lapsed_at")
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
