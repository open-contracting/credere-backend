"""rename lender field

Revision ID: df236486f60a
Revises: bfd66392691e
Create Date: 2023-06-20 13:08:37.396766

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "df236486f60a"
down_revision = "bfd66392691e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "lender",
        "borrowed_type_preferences",
        new_column_name="borrower_type_preferences",
    )


def downgrade() -> None:
    op.alter_column(
        "lender",
        "borrower_type_preferences",
        new_column_name="borrowed_type_preferences",
    )
