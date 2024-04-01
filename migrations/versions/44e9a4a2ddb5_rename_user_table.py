"""rename user table

Revision ID: 44e9a4a2ddb5
Revises: 63b0daed7f08
Create Date: 2023-09-07 20:34:06.547286

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "44e9a4a2ddb5"
down_revision = "63b0daed7f08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("user", "credere_user")
    op.drop_constraint("application_action_user_id_fkey", "application_action", type_="foreignkey")
    op.create_foreign_key(None, "application_action", "credere_user", ["user_id"], ["id"])
    # ### end Alembic commands ###


def downgrade() -> None:
    op.rename_table("credere_user", "user")
    op.drop_constraint(None, "application_action", type_="foreignkey")
    op.create_foreign_key(
        "application_action_user_id_fkey",
        "application_action",
        "user",
        ["user_id"],
        ["id"],
    )
    # ### end Alembic commands ###
