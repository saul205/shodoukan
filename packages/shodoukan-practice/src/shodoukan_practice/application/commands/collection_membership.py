"""Putting an item in a collection, for every use case that does.

Putting an item back in a copy it was taken out of (dismissed) undoes that:
it's the source's again, so updates from the source follow it once more.
"""

from ...domain.entities import (
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeKanji,
)
from ...domain.repositories import (
    EntryCollectionRepository,
    KanjiCollectionRepository,
)


def put_entry(
    collections: EntryCollectionRepository,
    collection: EntryCollection,
    entry: PracticeEntry,
) -> None:
    """Link `entry` to `collection`, lifting a dismissal of it there."""
    from_source = collection.source_collection_id is not None and (
        collections.undismiss_item(collection, entry.shared_key)
    )
    collections.add_item(collection, entry, from_source=from_source)


def put_kanji(
    collections: KanjiCollectionRepository,
    collection: KanjiCollection,
    kanji: PracticeKanji,
) -> None:
    """Link `kanji` to `collection`, lifting a dismissal of it there."""
    from_source = collection.source_collection_id is not None and (
        collections.undismiss_item(collection, kanji.shared_key)
    )
    collections.add_item(collection, kanji, from_source=from_source)
