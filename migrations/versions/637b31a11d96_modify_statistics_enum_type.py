"""modify statistics enum type

Revision ID: 637b31a11d96
Revises: 9455718e2178
Create Date: 2023-07-17 14:45:47.531660

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "637b31a11d96"
down_revision = "9455718e2178"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    op.alter_column("statistic", "updated_at", new_column_name="created_at")

    # create new type
    with op.get_context().autocommit_block():
        conn.execute(
            "CREATE TYPE statistic_type_new AS ENUM ('MSME_OPT_IN_STATISTICS', 'APPLICATION_KPIS');"
        )

    # change type of column to new type
    op.execute(
        """
        ALTER TABLE statistic
        ALTER COLUMN type TYPE statistic_type_new
        USING type::text::statistic_type_new
    """
    )

    # remove old type
    with op.get_context().autocommit_block():
        conn.execute("DROP TYPE statistic_type;")

    # rename new type
    with op.get_context().autocommit_block():
        conn.execute("ALTER TYPE statistic_type_new RENAME TO statistic_type;")

    # add lender_id column
    op.add_column("statistic", sa.Column("lender_id", sa.Integer))

    # add foreign key constraint
    op.create_foreign_key(None, "statistic", "lender", ["lender_id"], ["id"])


def downgrade() -> None:
    conn = op.get_bind()

    op.alter_column("statistic", "created_at", new_column_name="updated_at")

    # create old type
    with op.get_context().autocommit_block():
        conn.execute(
            "CREATE TYPE statistic_type_old AS ENUM ('MSME opt-in statistics', 'Application KPIs');"
        )

    # change type of column to old type
    op.execute(
        """
        ALTER TABLE statistic
        ALTER COLUMN type TYPE statistic_type_old
        USING type::text::statistic_type_old
    """
    )

    # remove new type
    with op.get_context().autocommit_block():
        conn.execute("DROP TYPE statistic_type;")

    # rename old type
    with op.get_context().autocommit_block():
        conn.execute("ALTER TYPE statistic_type_old RENAME TO statistic_type;")

    # drop foreign key
    op.drop_constraint("statistic_lender_id_fkey", "statistic", type_="foreignkey")

    # drop lender_id column
    op.drop_column("statistic", "lender_id")
