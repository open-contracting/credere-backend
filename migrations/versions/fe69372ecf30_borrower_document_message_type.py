"""borrower_document_message_type

Revision ID: fe69372ecf30
Revises: c919c4501192
Create Date: 2023-12-12 11:24:20.325769

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "fe69372ecf30"
down_revision = "c919c4501192"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
        ALTER TYPE message_type ADD VALUE IF NOT EXISTS 'BORROWER_DOCUMENT_UPDATED'
        """
        )
        op.execute(
            """
        ALTER TYPE message_type RENAME VALUE 'BORROWER_INVITACION' to 'BORROWER_INVITATION'
        """
        )
        op.execute(
            """
        ALTER TYPE message_type RENAME VALUE 'SUBMITION_COMPLETE' to 'SUBMISSION_COMPLETED'
        """
        )
        op.execute(
            """
        ALTER TYPE application_action_type RENAME VALUE 'BORROWER_DOCUMENT_UPDATE' to 'BORROWER_DOCUMENT_VERIFIED'
        """
        )


def downgrade() -> None:
    pass
