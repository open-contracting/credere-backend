"""new document type

Revision ID: 755091b6b4b4
Revises: d9b564fd6859
Create Date: 2024-08-24 13:18:08.143102

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "755091b6b4b4"
down_revision = "d9b564fd6859"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE borrower_document_type ADD VALUE IF NOT EXISTS 'INCOME_TAX_RETURN_STATEMENT'
      """
        )


def downgrade() -> None:
    pass
