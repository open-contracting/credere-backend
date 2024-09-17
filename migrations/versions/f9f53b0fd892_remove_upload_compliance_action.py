"""
remove upload-compliance action

Revision ID: f9f53b0fd892
Revises: 385fb9a01efc
Create Date: 2023-11-28 15:56:03.382365

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f9f53b0fd892"
down_revision = "385fb9a01efc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TYPE application_action_type_tmp AS ENUM ('AWARD_UPDATE', 'BORROWER_UPDATE',
        'APPLICATION_CALCULATOR_DATA_UPDATE', 'APPLICATION_CONFIRM_CREDIT_PRODUCT', 'FI_COMPLETE_APPLICATION',
        'FI_DOWNLOAD_DOCUMENT', 'FI_DOWNLOAD_APPLICATION', 'OCP_DOWNLOAD_APPLICATION', 'FI_START_APPLICATION',
        'FI_REQUEST_INFORMATION', 'OCP_DOWNLOAD_DOCUMENT', 'APPROVED_APPLICATION', 'REJECTED_APPLICATION',
        'MSME_UPLOAD_DOCUMENT', 'MSME_UPLOAD_CONTRACT', 'MSME_CHANGE_EMAIL', 'MSME_CONFIRM_EMAIL',
        'MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED', 'MSME_RETRY_APPLICATION', 'DATA_VALIDATION_UPDATE',
        'BORROWER_DOCUMENT_UPDATE', 'BORROWER_UPLOADED_CONTRACT', 'APPLICATION_COPIED_FROM', 'COPIED_APPLICATION');"""
    )
    op.execute("""DELETE from application_action where type = 'FI_UPLOAD_COMPLIANCE'""")

    op.execute(
        """ALTER TABLE application_action ALTER COLUMN type TYPE application_action_type_tmp
        USING (type::text::application_action_type_tmp);"""
    )

    op.execute("""DROP TYPE application_action_type""")

    op.execute("""ALTER TYPE application_action_type_tmp RENAME TO application_action_type;""")


def downgrade() -> None:
    pass
