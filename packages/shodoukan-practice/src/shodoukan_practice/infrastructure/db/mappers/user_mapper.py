from ....domain.entities import User
from ..orm import UserORM


def user_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        subject=row.subject,
        username=row.username,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def user_to_db(entity: User) -> UserORM:
    return UserORM(
        id=entity.id,
        subject=entity.subject,
        username=entity.username,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
