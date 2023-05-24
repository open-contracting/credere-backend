"""init

Revision ID: 2ca870aa737d
Revises:
Create Date: 2023-05-23 13:55:40.665762

"""
from sqlmodel import SQLModel, create_engine

from alembic import op
from app.core.settings import Settings
from app.schema.core_tables.core import Borrower
from app.schema.statistic_tables.statistic import Statistic
from app.schema.user_tables.users import User

# revision identifiers, used by Alembic.
revision = "2ca870aa737d"
down_revision = None
branch_labels = None
depends_on = None


SQLALCHEMY_DATABASE_URL = Settings().DB_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)


def upgrade() -> None:
    bind = op.get_bind()
    User.metadata.create_all(bind)
    Statistic.metadata.create_all(bind)
    Borrower.metadata.create_all(bind)
    # SQLModel.metadata.create_all(engine)


def downgrade() -> None:
    SQLModel.metadata.drop_all(engine)
