"""
add_borrower_document_update_to_application_type_enum

Revision ID: 8ab95d68febd
Revises: 0d937c85609d
Create Date: 2023-06-29 20:11:09.452203

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8ab95d68febd"
down_revision = "0d937c85609d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'DATA_VALIDATION_UPDATE'
        """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'BORROWER_DOCUMENT_UPDATE'
        """
        )


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
