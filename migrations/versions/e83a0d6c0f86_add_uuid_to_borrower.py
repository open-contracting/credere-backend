"""add_uuid_to_borrower

Revision ID: e83a0d6c0f86
Revises: df236486f60a
Create Date: 2023-06-27 11:43:24.186692

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e83a0d6c0f86"
down_revision = "df236486f60a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("borrower")

    for column in columns:
        if column["name"] == "uuid":
            break

    op.add_column("borrower", sa.Column("uuid", sa.String(), nullable=True, default=""))
    op.create_unique_constraint("uq_borrower_uuid", "borrower", ["uuid"])


def downgrade() -> None:
    op.drop_column("borrower", "uuid")
