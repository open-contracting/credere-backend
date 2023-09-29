"""additional info

Revision ID: 3f575f86f623
Revises: 791d69d98498
Create Date: 2023-09-28 23:17:26.123522

"""
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3f575f86f623'
down_revision = '791d69d98498'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('credit_product', 'interest_rate', type_=postgresql.VARCHAR(450))


def downgrade() -> None:
    op.alter_column('credit_product', 'interest_rate', type_=postgresql.VARCHAR(140),
                    postgresql_using='interest_rate::varchar(140)')
