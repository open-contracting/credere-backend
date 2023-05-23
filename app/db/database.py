from sqlmodel import create_engine

from app.core.settings import Settings

SQLALCHEMY_DATABASE_URL = Settings().DB_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=True)
