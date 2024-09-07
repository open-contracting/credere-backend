"""remove compliance doc type

Revision ID: c919c4501192
Revises: f9f53b0fd892
Create Date: 2023-11-28 16:31:35.726353

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c919c4501192"
down_revision = "f9f53b0fd892"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """create type borrower_document_type_tmp as enum ('INCORPORATION_DOCUMENT', 'SUPPLIER_REGISTRATION_DOCUMENT',
        'BANK_NAME', 'BANK_CERTIFICATION_DOCUMENT', 'FINANCIAL_STATEMENT', 'SIGNED_CONTRACT',
        'SHAREHOLDER_COMPOSITION', 'CHAMBER_OF_COMMERCE', 'THREE_LAST_BANK_STATEMENT');"""
    )
    op.execute("""DELETE from borrower_document where type = 'COMPLIANCE_REPORT'""")

    op.execute(
        """ALTER TABLE borrower_document ALTER COLUMN type TYPE borrower_document_type_tmp
        USING (type::text::borrower_document_type_tmp);"""
    )

    op.execute("""DROP TYPE borrower_document_type""")

    op.execute("""ALTER TYPE borrower_document_type_tmp RENAME TO borrower_document_type;""")


def downgrade() -> None:
    pass
