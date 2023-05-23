"""init

Revision ID: 2ca870aa737d
Revises:
Create Date: 2023-05-23 13:55:40.665762

"""
from sqlmodel import SQLModel, create_engine

from app.core.settings import Settings

# revision identifiers, used by Alembic.
revision = "2ca870aa737d"
down_revision = None
branch_labels = None
depends_on = None


SQLALCHEMY_DATABASE_URL = Settings().DB_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)

SQLModel.metadata.create_all(engine)


# in case of related DBs we just need one model to generate the rest
def upgrade() -> None:
    SQLModel.metadata.create_all(engine)


def downgrade() -> None:
    SQLModel.metadata.drop_all(engine)
