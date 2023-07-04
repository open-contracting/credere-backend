from sqlalchemy.orm import Session

from app.schema.api import UserListResponse

from ..schema import core


def get_all_users(session: Session) -> UserListResponse:
    users_query = session.query(core.User)

    total_count = users_query.count()

    users = users_query.all()

    return UserListResponse(
        items=users,
        count=total_count,
        page=0,
        page_size=total_count,
    )
