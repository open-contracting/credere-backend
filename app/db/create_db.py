from sqlmodel import SQLModel
from database import engine

print("Generating database")

SQLModel.metadata.create_all(engine)
