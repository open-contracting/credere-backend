"""
remove contract upload logic

Revision ID: da089b31d013
Revises: d77ac01b9718
Create Date: 2024-10-07 10:13:41.967830

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "da089b31d013"
down_revision = "d77ac01b9718"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Application status, COMPLETED is now APPROVED, and COMPLETED AND CONTRACT_UPLOADED no longer exists
    op.execute("""
        UPDATE application set status = 'STARTED' where status in ('APPROVED', 'CONTRACT_UPLOADED')
    """)
    op.execute("""
        UPDATE application set status = 'APPROVED' where status = 'COMPLETED'
    """)

    op.execute("""
        UPDATE application set lender_approved_at = lender_completed_at
    """)

    # Remove no longer used MessageType and update CREDIT_DISBURSED to APPROVED_APPLICATION
    op.execute("""
        DELETE FROM message where type in ('CONTRACT_UPLOAD_REQUEST',
        'CONTRACT_UPLOAD_CONFIRMATION', 'CONTRACT_UPLOAD_CONFIRMATION_TO_FI', 'APPROVED_APPLICATION')
    """)
    op.execute("""
    UPDATE message set type = 'APPROVED_APPLICATION' where type = 'CREDIT_DISBURSED'
    """)
    op.execute("""
        CREATE TYPE message_type_tmp as ENUM ('BORROWER_INVITATION', 'BORROWER_PENDING_APPLICATION_REMINDER',
        'BORROWER_PENDING_SUBMIT_REMINDER', 'SUBMISSION_COMPLETED', 'NEW_APPLICATION_OCP', 'NEW_APPLICATION_FI',
        'FI_MESSAGE', 'APPROVED_APPLICATION', 'REJECTED_APPLICATION', 'OVERDUE_APPLICATION',
        'EMAIL_CHANGE_CONFIRMATION', 'APPLICATION_COPIED', 'BORROWER_DOCUMENT_UPDATED');
    """)
    op.execute("""
        ALTER table message ALTER COLUMN type TYPE message_type_tmp USING (type::text::message_type_tmp)
    """)
    op.execute("DROP TYPE message_type")
    op.execute("ALTER TYPE message_type_tmp RENAME TO message_type")

    # Remove no longer used ApplicationActionType and update FI_COMPLETE_APPLICATION to APPROVED_APPLICATION
    op.execute("""
        DELETE FROM application_action where type in ('MSME_UPLOAD_CONTRACT', 'BORROWER_UPLOADED_CONTRACT',
        'APPROVED_APPLICATION')
    """)
    op.execute("""
    UPDATE application_action set type = 'APPROVED_APPLICATION' where type = 'FI_COMPLETE_APPLICATION'
    """)
    op.execute("""
        CREATE TYPE application_action_type_tmp AS ENUM ('AWARD_UPDATE', 'BORROWER_UPDATE',
        'APPLICATION_CALCULATOR_DATA_UPDATE',
        'APPLICATION_CONFIRM_CREDIT_PRODUCT',
        'FI_DOWNLOAD_DOCUMENT', 'FI_DOWNLOAD_APPLICATION', 'OCP_DOWNLOAD_APPLICATION',
        'FI_START_APPLICATION', 'FI_REQUEST_INFORMATION', 'OCP_DOWNLOAD_DOCUMENT',
        'APPROVED_APPLICATION', 'REJECTED_APPLICATION',
        'MSME_UPLOAD_DOCUMENT',
        'MSME_CHANGE_EMAIL', 'MSME_CONFIRM_EMAIL',
        'MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED', 'MSME_RETRY_APPLICATION', 'DATA_VALIDATION_UPDATE',
        'BORROWER_DOCUMENT_VERIFIED', 'APPLICATION_COPIED_FROM', 'COPIED_APPLICATION',
        'APPLICATION_ROLLBACK_SELECT_PRODUCT', 'APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT');
    """)
    op.execute("""
        ALTER table application_action ALTER COLUMN type TYPE application_action_type_tmp
        USING (type::text::application_action_type_tmp)
    """)
    op.execute("DROP TYPE application_action_type")
    op.execute("ALTER TYPE application_action_type_tmp RENAME TO application_action_type")

    # Drop no longer used columns
    op.drop_column("application", "lender_completed_at")
    op.drop_column("application", "borrower_uploaded_contract_at")
    op.drop_column("application", "contract_amount_submitted")


def downgrade() -> None:
    op.add_column(
        "application",
        sa.Column("contract_amount_submitted", sa.NUMERIC(precision=16, scale=2), autoincrement=False, nullable=True),
    )
    op.add_column(
        "application",
        sa.Column(
            "borrower_uploaded_contract_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "application",
        sa.Column("lender_completed_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    )
