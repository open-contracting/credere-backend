"""new document types

Revision ID: 03e96ecd4e99
Revises: a03836bf1cdf
Create Date: 2023-08-30 19:54:08.362759

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "03e96ecd4e99"
down_revision = "a03836bf1cdf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE borrower_document_type ADD VALUE IF NOT EXISTS 'SHAREHOLDER_COMPOSITION'
      """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE borrower_document_type ADD VALUE IF NOT EXISTS 'CHAMBER_OF_COMMERCE'
      """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE borrower_document_type ADD VALUE IF NOT EXISTS 'THREE_LAST_BANK_STATEMENT'
      """
        )


def downgrade() -> None:
    pass
