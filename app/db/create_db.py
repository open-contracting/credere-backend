from database import engine
from sqlmodel import SQLModel

print("Generating database")

SQLModel.metadata.create_all(engine)
