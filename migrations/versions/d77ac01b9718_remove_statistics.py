"""
remove statistics

Revision ID: d77ac01b9718
Revises: db1054a56c3c
Create Date: 2024-09-06 13:30:46.828306

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d77ac01b9718"
down_revision = "db1054a56c3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("statistic")


def downgrade() -> None:
    op.create_table(
        "statistic",
        sa.Column(
            "type",
            postgresql.ENUM("MSME_OPT_IN_STATISTICS", "APPLICATION_KPIS", name="statistic_type"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("lender_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(["lender_id"], ["lender.id"], name="statistic_lender_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="statistic_pkey"),
    )
