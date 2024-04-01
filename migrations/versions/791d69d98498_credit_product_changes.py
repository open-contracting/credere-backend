"""credit product changes

Revision ID: 791d69d98498
Revises: daa51e9c149b
Create Date: 2023-09-20 14:51:43.657587

"""

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "791d69d98498"
down_revision = "daa51e9c149b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "credit_product",
        sa.Column(
            "additional_information",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column(
        "credit_product",
        "interest_rate",
        type_=postgresql.VARCHAR(140),
        postgresql_using="interest_rate::varchar(140)",
    )


def downgrade() -> None:
    op.drop_column("credit_product", "additional_information")
    op.alter_column(
        "credit_product",
        "interest_rate",
        type_=postgresql.NUMERIC(5, 2),
        postgresql_using="interest_rate::int",
    )
