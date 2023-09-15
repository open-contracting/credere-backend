"""lender logo

Revision ID: daa51e9c149b
Revises: 44e9a4a2ddb5
Create Date: 2023-09-14 19:56:48.874396

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'daa51e9c149b'
down_revision = '44e9a4a2ddb5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lender", sa.Column("logo_filename", sa.String()))
    op.execute("UPDATE lender set logo_filename = ''")


def downgrade() -> None:
    op.drop_column("lender", "logo_filename")
