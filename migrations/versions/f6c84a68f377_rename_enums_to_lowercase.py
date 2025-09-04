"""
rename_enums_to_lowercase

Revision ID: f6c84a68f377
Revises: f4f2b2a76181
Create Date: 2025-09-04 00:08:50.724202

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f6c84a68f377"
down_revision = "f4f2b2a76181"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename enum types from snake_case to lowercase to match SQLModel conventions
    op.execute("ALTER TYPE borrower_size RENAME TO borrowersize")
    op.execute("ALTER TYPE credit_type RENAME TO credittype")
    op.execute("ALTER TYPE borrower_status RENAME TO borrowerstatus")
    op.execute("ALTER TYPE application_status RENAME TO applicationstatus")
    op.execute("ALTER TYPE borrower_document_type RENAME TO borrowerdocumenttype")
    op.execute("ALTER TYPE message_type RENAME TO messagetype")
    op.execute("ALTER TYPE user_type RENAME TO usertype")
    op.execute("ALTER TYPE application_action_type RENAME TO applicationactiontype")


def downgrade() -> None:
    # Revert enum type names back to snake_case
    op.execute("ALTER TYPE applicationactiontype RENAME TO application_action_type")
    op.execute("ALTER TYPE usertype RENAME TO user_type")
    op.execute("ALTER TYPE messagetype RENAME TO message_type")
    op.execute("ALTER TYPE borrowerdocumenttype RENAME TO borrower_document_type")
    op.execute("ALTER TYPE applicationstatus RENAME TO application_status")
    op.execute("ALTER TYPE borrowerstatus RENAME TO borrower_status")
    op.execute("ALTER TYPE credittype RENAME TO credit_type")
    op.execute("ALTER TYPE borrowersize RENAME TO borrower_size")
