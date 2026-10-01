"""Response models for the current user."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID  # the identity provider's user id
    username: str
    created_at: datetime
