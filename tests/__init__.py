from typing import Generator

from sqlalchemy.orm import Session, sessionmaker


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


def get_test_db(engine):
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def inner() -> Generator[Session, None, None]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    return inner
