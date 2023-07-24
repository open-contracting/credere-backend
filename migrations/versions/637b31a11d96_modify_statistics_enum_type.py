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
    # rename column updated_at to created_at
    op.alter_column("statistic", "updated_at", new_column_name="created_at")

    # create new type
    op.execute(
        "CREATE TYPE statistic_type_new AS ENUM ('MSME_OPT_IN_STATISTICS', 'APPLICATION_KPIS');"
    )

    # add a temporary column of new type
    op.add_column(
        "statistic",
        sa.Column(
            "type_temp",
            sa.Enum(
                "MSME_OPT_IN_STATISTICS", "APPLICATION_KPIS", name="statistic_type_new"
            ),
        ),
    )

    # copy data from old column to temporary column
    op.execute("UPDATE statistic SET type_temp=type::text::statistic_type_new;")

    # drop old column
    op.drop_column("statistic", "type")

    # rename temporary column to old column's name
    op.alter_column("statistic", "type_temp", new_column_name="type")

    # drop old type if it exists
    op.execute("DROP TYPE IF EXISTS statistic_type;")

    # rename new type
    op.execute("ALTER TYPE statistic_type_new RENAME TO statistic_type;")

    # add lender_id column
    op.add_column("statistic", sa.Column("lender_id", sa.Integer))

    # add foreign key constraint
    op.create_foreign_key(None, "statistic", "lender", ["lender_id"], ["id"])


def downgrade() -> None:
    # rename column created_at back to updated_at
    op.alter_column("statistic", "created_at", new_column_name="updated_at")

    # create old type
    op.execute(
        "CREATE TYPE statistic_type_old AS ENUM ('MSME opt-in statistics', 'Application KPIs');"
    )

    # add a temporary column of old type
    op.add_column(
        "statistic",
        sa.Column(
            "type_temp",
            sa.Enum(
                "MSME opt-in statistics", "Application KPIs", name="statistic_type_old"
            ),
        ),
    )

    # copy data from old column to temporary column
    op.execute("UPDATE statistic SET type_temp=type::text::statistic_type_old;")

    # drop old column
    op.drop_column("statistic", "type")

    # rename temporary column to old column's name
    op.alter_column("statistic", "type_temp", new_column_name="type")

    # drop new type if it exists
    op.execute("DROP TYPE IF EXISTS statistic_type;")

    # rename old type
    op.execute("ALTER TYPE statistic_type_old RENAME TO statistic_type;")

    # drop foreign key
    op.drop_constraint("statistic_lender_id_fkey", "statistic", type_="foreignkey")

    # drop lender_id column
    op.drop_column("statistic", "lender_id")
