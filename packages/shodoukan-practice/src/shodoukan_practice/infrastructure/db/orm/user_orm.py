import datetime
import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import Base, created_at_column, updated_at_column


class UserORM(Base):
    __tablename__ = "users"

    # The identity provider's user id (the access token's `sub`), not generated
    # here: practice users map 1:1 to provider users.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    # Display name from the identity provider; not unique, not an identity.
    username: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()
