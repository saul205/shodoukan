import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base_orm import Base, created_at_column, updated_at_column


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime.datetime] = created_at_column()
    updated_at: Mapped[datetime.datetime] = updated_at_column()
