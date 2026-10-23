"""Base for aggregates that record when they were created and last changed.

The domain owns these dates: they default to "now" when the entity is
created, and every method that changes an aggregate's state calls `touch()`.
Aggregates are changed only through their methods, so `updated_at` moves
with any change.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..clock import utc_now


class TimestampedEntity(BaseModel):
    # Methods assign fields; validate them like the constructor does.
    model_config = ConfigDict(validate_assignment=True)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()
