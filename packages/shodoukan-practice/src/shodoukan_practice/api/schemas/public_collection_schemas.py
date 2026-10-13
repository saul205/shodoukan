"""Request and response models for sharing collections.

Public collections of both kinds share these models; the route says which
kind it is. A preview's items are the library's `PracticeEntryResponse` /
`PracticeKanjiResponse`, numbered (`preview_ids`) since they aren't stored.
"""

from datetime import datetime
from typing import Annotated, Any, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from ...domain.entities import Collection
from ...domain.searches import PublicCollectionSummary

C = TypeVar("C", bound=Collection)

PublicOwnerQuery = Literal["mine", "others", "all"]
PublicSortQuery = Annotated[
    Literal["popular", "recent"],
    Field(description="`popular`: most downloaded first; `recent`: newest first."),
]


class PublicationRequest(BaseModel):
    include_notes: bool = Field(
        default=False,
        description="Publish the owner's notes (entry, sense, kanji) too.",
    )


class PublicCollectionResponse(BaseModel):
    id: int
    name: str
    description: str | None
    owner: str = Field(description="The owner's username (a display name).")
    is_mine: bool
    version: int
    published_at: datetime
    item_count: int = Field(description="Items in the published version.")
    downloads: int = Field(description="Users who imported it, its owner apart.")
    imported_version: int | None = Field(
        description="The version the current user last imported, if they did."
    )

    @classmethod
    def from_summary(
        cls, summary: PublicCollectionSummary[C], viewer_id: UUID
    ) -> "PublicCollectionResponse":
        collection = summary.collection
        assert collection.id is not None and collection.published_at is not None
        return cls(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            owner=summary.owner_username,
            is_mine=collection.user_id == viewer_id,
            version=collection.published_version,
            published_at=collection.published_at,
            item_count=summary.item_count,
            downloads=summary.downloads,
            imported_version=summary.viewer_version,
        )


class PublicCollectionPageResponse(BaseModel):
    items: list[PublicCollectionResponse]
    total: int  # collections matching the request, across every page
    limit: int
    offset: int


def preview_ids(item: dict[str, Any], start: int) -> dict[str, Any]:
    """`item` (a dumped preview item) with an id for it and each nested part
    that has none, counting from `start`: unstored, they only need one to be
    told apart on the page."""
    ids = iter(range(start, start + 1_000_000))

    def number(value: Any) -> Any:
        if isinstance(value, dict):
            numbered = {key: number(v) for key, v in value.items()}
            if "id" in numbered and numbered["id"] is None:
                numbered["id"] = next(ids)
            return numbered
        if isinstance(value, list):
            return [number(v) for v in value]
        return value

    result: dict[str, Any] = number(item)
    return result
