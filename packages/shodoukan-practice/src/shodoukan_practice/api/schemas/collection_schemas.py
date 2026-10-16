"""Request and response models for entry and kanji collections.

Both kinds share these models; the route says which kind it is. Items in a
collection are returned with the library's `PracticeEntryResponse` /
`PracticeKanjiResponse`.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ...domain.entities import (
    COLLECTION_NAME_MAX_LENGTH,
    SharedEntryCollection,
    SharedKanjiCollection,
)

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
    is_public: bool
    published_version: int = Field(description="Latest published version; 0 if never.")
    published_at: datetime | None
    source_collection_id: int | None = Field(
        description="The collection this one was imported from, if any."
    )
    source_version: int | None = Field(
        description="The version of its source it was imported from, if public."
    )
    latest_source_version: int | None = Field(
        default=None,
        description=(
            "Its source's latest published version, while the source is public: "
            "a newer one than `source_version` can be applied with `POST .../update`."
        ),
    )
    created_at: datetime
    updated_at: datetime


# --- Export and import ---

CollectionFileFormat = Literal["shodoukan.collection"]
# Bumped when a file of the new version can't be read as the old one.
CollectionFileVersion = Literal[1]


class CollectionFile(BaseModel):
    """An exported collection, as downloaded and imported back.

    `collection` is the domain's portable form as is (like exercise
    settings): the file format is the import contract.
    """

    format: CollectionFileFormat
    version: CollectionFileVersion
    exported_at: datetime | None = None


class EntryCollectionFile(CollectionFile):
    kind: Literal["entries"]
    collection: SharedEntryCollection


class KanjiCollectionFile(CollectionFile):
    kind: Literal["kanji"]
    collection: SharedKanjiCollection


class CollectionImportResponse(BaseModel):
    """The new collection, and what the import did with the items."""

    collection: CollectionResponse
    created: int = Field(description="Items added to the library.")
    existing: int = Field(
        description="Items already in the library; their own data was merged in."
    )


class EntryCollectionImportResponse(CollectionImportResponse):
    missing: list[int] = Field(
        description="`source_entry_id`s the dictionary no longer has, left out."
    )


class KanjiCollectionImportResponse(CollectionImportResponse):
    missing: list[str] = Field(
        description="Kanji the dictionary doesn't have, left out."
    )


class EntryCollectionUpdateResponse(EntryCollectionImportResponse):
    removed: int = Field(description="Items the source dropped, taken out of it.")


class KanjiCollectionUpdateResponse(KanjiCollectionImportResponse):
    removed: int = Field(description="Items the source dropped, taken out of it.")
