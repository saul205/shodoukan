"""User-defined grouping of either entries or kanji from the user's library.

A collection never copies data and doesn't hold its members either: this
entity is only the collection's metadata. Membership lives in a link table
(m:n) and is read and changed through the repositories, so listing a
collection's cards or tagging one item never loads the whole membership.

The same concept doubles as a tag — assigning the tag "verbs" to an entry
is adding that entry to the "verbs" collection — so there is no separate Tag
entity.

Entries and kanji are never mixed: the subclass says which one a collection
holds. Their ids come from different tables and can collide, so repositories
take the typed entity rather than a bare id.
"""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from ..clock import utc_now
from .timestamped_entity import TimestampedEntity

COLLECTION_NAME_MAX_LENGTH = 100


class Collection(TimestampedEntity):
    """Shared base; instantiate `EntryCollection` or `KanjiCollection`."""

    id: int | None
    user_id: UUID
    name: str = Field(min_length=1, max_length=COLLECTION_NAME_MAX_LENGTH)
    description: str | None = None
    # Sharing it: whether others can see it, and its latest published
    # version (0 = never published; the snapshot is stored apart).
    is_public: bool = False
    published_version: int = 0
    published_at: datetime | None = None
    # The collection this one was imported from, if any, and the version
    # imported. No link: it may belong to another user and be gone.
    source_collection_id: int | None = None
    source_version: int | None = None

    def rename(self, name: str) -> None:
        if name != self.name:
            self.name = name
            self.touch()

    def describe(self, description: str | None) -> None:
        if description != self.description:
            self.description = description
            self.touch()

    def publish(self) -> int:
        """Make it public with a new version (its snapshot is the caller's to
        store); returns the version."""
        self.published_version += 1
        self.published_at = utc_now()
        self.is_public = True
        self.touch()
        return self.published_version

    def follow_source(self, version: int) -> None:
        """Record that this copy now follows `version` of its source."""
        if version != self.source_version:
            self.source_version = version
            self.touch()

    def unpublish(self) -> None:
        """Hide it from others; its last version is kept for publishing again."""
        if self.is_public:
            self.is_public = False
            self.touch()


class EntryCollection(Collection):
    """Groups `PracticeEntry` items."""


class KanjiCollection(Collection):
    """Groups `PracticeKanji` items."""
