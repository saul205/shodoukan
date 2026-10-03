"""Request and response models for entry and kanji collections.

Both kinds share these models; the route says which kind it is. Items in a
collection are returned with the library's `PracticeEntryResponse` /
`PracticeKanjiResponse`.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ...domain.entities import COLLECTION_NAME_MAX_LENGTH

CollectionName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=COLLECTION_NAME_MAX_LENGTH
    ),
]


class CollectionRequest(BaseModel):
    """A collection's editable fields. Updates replace both."""

    name: CollectionName = Field(description="Unique among the user's collections.")
    description: str | None = None


class CollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
