"""init

Revision ID: 2ca870aa737d
Revises:
Create Date: 2023-05-23 13:55:40.665762

"""
from sqlmodel import create_engine

from alembic import op
from app.core.settings import app_settings
from app.schema.core_tables.core import Borrower
from app.schema.statistic_tables.statistic import Statistic
from app.schema.user_tables.users import User

# revision identifiers, used by Alembic.
revision = "2ca870aa737d"
down_revision = None
branch_labels = None
depends_on = None


SQLALCHEMY_DATABASE_URL = app_settings.db_url

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)


# SQLModel.metadata.create_all() is not properly generations tables,
# alternative approach would be using one table metadata to create it and all linked tables
def upgrade() -> None:
    bind = op.get_bind()
    User.metadata.create_all(bind)
    Statistic.metadata.create_all(bind)
    Borrower.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    User.metadata.drop_all(bind)
    Statistic.metadata.drop_all(bind)
    Borrower.metadata.drop_all(bind)
