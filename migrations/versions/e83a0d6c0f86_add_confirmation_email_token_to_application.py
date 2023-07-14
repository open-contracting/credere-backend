"""add_confirmation_email_token_to_application

Revision ID: e83a0d6c0f86
Revises: 9df7f1e04a80
Create Date: 2023-06-27 11:43:24.186692

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "e83a0d6c0f86"
down_revision = "9df7f1e04a80"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = inspector.get_columns("application")

    column_info = None
    for column in columns:
        if column["name"] == "confirmation_email_token":
            column_info = column["name"]
            break

    if column_info is not None:
        return

    op.add_column(
        "application",
        sa.Column("confirmation_email_token", sa.String(), nullable=True, default=""),
    )

    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE message_type ADD VALUE IF NOT EXISTS 'EMAIL_CHANGE_CONFIRMATION'
      """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'FI_DOWNLOAD_DOCUMENT'
      """
        )
    with op.get_context().autocommit_block():
        op.execute(
            """
          ALTER TYPE application_action_type ADD VALUE IF NOT EXISTS 'OCP_DOWNLOAD_DOCUMENT'
      """
        )


def downgrade() -> None:
    op.drop_column("application", "confirmation_email_token")
