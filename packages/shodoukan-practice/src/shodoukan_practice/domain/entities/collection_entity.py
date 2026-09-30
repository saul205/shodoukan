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

from pydantic import BaseModel, Field


class Collection(BaseModel):
    """Shared base; instantiate `EntryCollection` or `KanjiCollection`."""

    id: int | None
    user_id: int
    name: str = Field(min_length=1)
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class EntryCollection(Collection):
    """Groups `PracticeEntry` items."""


class KanjiCollection(Collection):
    """Groups `PracticeKanji` items."""
