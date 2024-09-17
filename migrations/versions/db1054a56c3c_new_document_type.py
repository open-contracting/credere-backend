"""
new document type

Revision ID: db1054a56c3c
Revises: 1fa1da5eb109
Create Date: 2024-08-30 16:58:09.584088

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "db1054a56c3c"
down_revision = "1fa1da5eb109"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE borrower_document_type ADD VALUE IF NOT EXISTS 'CHAMBER_OF_COMMERCE_WITH_TEMPORARY_UNIONS'
      """
        )


def downgrade() -> None:
    pass
