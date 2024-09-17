"""
make str nonnullable

Revision ID: d5f6a158acf0
Revises: beaafd626a26
Create Date: 2024-08-19 16:53:38.130096

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d5f6a158acf0"
down_revision = "beaafd626a26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "application",
        "status",
        existing_type=postgresql.ENUM(
            "PENDING",
            "ACCEPTED",
            "LAPSED",
            "DECLINED",
            "SUBMITTED",
            "STARTED",
            "APPROVED",
            "CONTRACT_UPLOADED",
            "COMPLETED",
            "REJECTED",
            "INFORMATION_REQUESTED",
            name="application_status",
        ),
        nullable=False,
    )
    op.alter_column("application", "confirmation_email_token", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column(
        "application_action",
        "type",
        existing_type=postgresql.ENUM(
            "AWARD_UPDATE",
            "BORROWER_UPDATE",
            "APPLICATION_CALCULATOR_DATA_UPDATE",
            "APPLICATION_CONFIRM_CREDIT_PRODUCT",
            "FI_COMPLETE_APPLICATION",
            "FI_DOWNLOAD_DOCUMENT",
            "FI_DOWNLOAD_APPLICATION",
            "OCP_DOWNLOAD_APPLICATION",
            "FI_START_APPLICATION",
            "FI_REQUEST_INFORMATION",
            "OCP_DOWNLOAD_DOCUMENT",
            "APPROVED_APPLICATION",
            "REJECTED_APPLICATION",
            "MSME_UPLOAD_DOCUMENT",
            "MSME_UPLOAD_CONTRACT",
            "MSME_CHANGE_EMAIL",
            "MSME_CONFIRM_EMAIL",
            "MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED",
            "MSME_RETRY_APPLICATION",
            "DATA_VALIDATION_UPDATE",
            "BORROWER_DOCUMENT_VERIFIED",
            "BORROWER_UPLOADED_CONTRACT",
            "APPLICATION_COPIED_FROM",
            "COPIED_APPLICATION",
            "APPLICATION_ROLLBACK_SELECT_PRODUCT",
            "APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT",
            name="application_action_type",
        ),
        nullable=False,
    )
    op.alter_column(
        "borrower",
        "size",
        existing_type=postgresql.ENUM("NOT_INFORMED", "MICRO", "SMALL", "MEDIUM", "BIG", name="borrower_size"),
        nullable=False,
    )
    op.alter_column(
        "borrower",
        "status",
        existing_type=postgresql.ENUM("ACTIVE", "DECLINE_OPPORTUNITIES", name="borrower_status"),
        nullable=False,
    )
    op.alter_column(
        "credere_user", "type", existing_type=postgresql.ENUM("OCP", "FI", name="user_type"), nullable=False
    )
    op.alter_column("lender", "logo_filename", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column(
        "lender",
        "default_pre_approval_message",
        existing_type=sa.VARCHAR(),
        nullable=False,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column(
        "message",
        "type",
        existing_type=postgresql.ENUM(
            "BORROWER_INVITATION",
            "BORROWER_PENDING_APPLICATION_REMINDER",
            "BORROWER_PENDING_SUBMIT_REMINDER",
            "SUBMISSION_COMPLETED",
            "CONTRACT_UPLOAD_REQUEST",
            "CONTRACT_UPLOAD_CONFIRMATION",
            "CONTRACT_UPLOAD_CONFIRMATION_TO_FI",
            "NEW_APPLICATION_OCP",
            "NEW_APPLICATION_FI",
            "FI_MESSAGE",
            "APPROVED_APPLICATION",
            "REJECTED_APPLICATION",
            "OVERDUE_APPLICATION",
            "EMAIL_CHANGE_CONFIRMATION",
            "APPLICATION_COPIED",
            "CREDIT_DISBURSED",
            "BORROWER_DOCUMENT_UPDATED",
            name="message_type",
        ),
        nullable=False,
    )
    op.alter_column("message", "external_message_id", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column("message", "body", existing_type=sa.VARCHAR(), nullable=False)
    op.alter_column(
        "statistic",
        "type",
        existing_type=postgresql.ENUM("MSME_OPT_IN_STATISTICS", "APPLICATION_KPIS", name="statistic_type"),
        nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "statistic",
        "type",
        existing_type=postgresql.ENUM("MSME_OPT_IN_STATISTICS", "APPLICATION_KPIS", name="statistic_type"),
        nullable=True,
    )
    op.alter_column("message", "body", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column("message", "external_message_id", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column(
        "message",
        "type",
        existing_type=postgresql.ENUM(
            "BORROWER_INVITATION",
            "BORROWER_PENDING_APPLICATION_REMINDER",
            "BORROWER_PENDING_SUBMIT_REMINDER",
            "SUBMISSION_COMPLETED",
            "CONTRACT_UPLOAD_REQUEST",
            "CONTRACT_UPLOAD_CONFIRMATION",
            "CONTRACT_UPLOAD_CONFIRMATION_TO_FI",
            "NEW_APPLICATION_OCP",
            "NEW_APPLICATION_FI",
            "FI_MESSAGE",
            "APPROVED_APPLICATION",
            "REJECTED_APPLICATION",
            "OVERDUE_APPLICATION",
            "EMAIL_CHANGE_CONFIRMATION",
            "APPLICATION_COPIED",
            "CREDIT_DISBURSED",
            "BORROWER_DOCUMENT_UPDATED",
            name="message_type",
        ),
        nullable=True,
    )
    op.alter_column(
        "lender",
        "default_pre_approval_message",
        existing_type=sa.VARCHAR(),
        nullable=True,
        existing_server_default=sa.text("''::character varying"),
    )
    op.alter_column("lender", "logo_filename", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column(
        "credere_user", "type", existing_type=postgresql.ENUM("OCP", "FI", name="user_type"), nullable=True
    )
    op.alter_column(
        "borrower",
        "status",
        existing_type=postgresql.ENUM("ACTIVE", "DECLINE_OPPORTUNITIES", name="borrower_status"),
        nullable=True,
    )
    op.alter_column(
        "borrower",
        "size",
        existing_type=postgresql.ENUM("NOT_INFORMED", "MICRO", "SMALL", "MEDIUM", "BIG", name="borrower_size"),
        nullable=True,
    )
    op.alter_column(
        "application_action",
        "type",
        existing_type=postgresql.ENUM(
            "AWARD_UPDATE",
            "BORROWER_UPDATE",
            "APPLICATION_CALCULATOR_DATA_UPDATE",
            "APPLICATION_CONFIRM_CREDIT_PRODUCT",
            "FI_COMPLETE_APPLICATION",
            "FI_DOWNLOAD_DOCUMENT",
            "FI_DOWNLOAD_APPLICATION",
            "OCP_DOWNLOAD_APPLICATION",
            "FI_START_APPLICATION",
            "FI_REQUEST_INFORMATION",
            "OCP_DOWNLOAD_DOCUMENT",
            "APPROVED_APPLICATION",
            "REJECTED_APPLICATION",
            "MSME_UPLOAD_DOCUMENT",
            "MSME_UPLOAD_CONTRACT",
            "MSME_CHANGE_EMAIL",
            "MSME_CONFIRM_EMAIL",
            "MSME_UPLOAD_ADDITIONAL_DOCUMENT_COMPLETED",
            "MSME_RETRY_APPLICATION",
            "DATA_VALIDATION_UPDATE",
            "BORROWER_DOCUMENT_VERIFIED",
            "BORROWER_UPLOADED_CONTRACT",
            "APPLICATION_COPIED_FROM",
            "COPIED_APPLICATION",
            "APPLICATION_ROLLBACK_SELECT_PRODUCT",
            "APPLICATION_ROLLBACK_CONFIRM_CREDIT_PRODUCT",
            name="application_action_type",
        ),
        nullable=True,
    )
    op.alter_column("application", "confirmation_email_token", existing_type=sa.VARCHAR(), nullable=True)
    op.alter_column(
        "application",
        "status",
        existing_type=postgresql.ENUM(
            "PENDING",
            "ACCEPTED",
            "LAPSED",
            "DECLINED",
            "SUBMITTED",
            "STARTED",
            "APPROVED",
            "CONTRACT_UPLOADED",
            "COMPLETED",
            "REJECTED",
            "INFORMATION_REQUESTED",
            name="application_status",
        ),
        nullable=True,
    )
    # ### end Alembic commands ###
