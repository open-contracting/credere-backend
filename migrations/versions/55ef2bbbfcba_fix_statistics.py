"""fix statistics

Revision ID: 55ef2bbbfcba
Revises: 3f575f86f623
Create Date: 2023-10-09 15:26:07.087859

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '55ef2bbbfcba'
down_revision = '3f575f86f623'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('statistic_lender_id_fkey', 'statistic', type_='foreignkey')
    op.create_foreign_key('statistic_lender_id_fkey', 'statistic', 'lender', ['lender_id'], ['id'],)


def downgrade() -> None:
    op.drop_constraint('statistic_lender_id_fkey', 'statistic', type_='foreignkey')
    op.create_foreign_key('statistic_lender_id_fkey', 'award', 'lender', ['lender_id'], ['id'],)
