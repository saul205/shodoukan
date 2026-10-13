import pytest
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import (
    CollectionUpdate,
    CreateEntryCollection,
    ImportEntry,
    ImportPublicEntryCollection,
    PublishEntryCollection,
    RemoveEntryFromCollection,
    UnpublishEntryCollection,
    UpdateEntryCollectionFromSource,
)
from shodoukan_practice.domain.entities import EntryCollection, PracticeEntry
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.domain.searches import PublicCollectionSearch
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
)


@pytest.fixture
def collections(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def entries(session: Session) -> SqlAlchemyPracticeEntryRepository:
    return SqlAlchemyPracticeEntryRepository(session)


@pytest.fixture
def gateway(dictionary: Dictionary) -> ShodoukanDictionaryGateway:
    return ShodoukanDictionaryGateway(dictionary)


@pytest.fixture
def verbs(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    user: UserORM,
) -> EntryCollection:
    """The user's "verbs": 食べる (with a note and their own meaning) and 水,
    which they deactivated."""
    collection = CreateEntryCollection(collections).execute(user.id, "verbs")
    importer = ImportEntry(gateway, entries, collections)
    eat = importer.execute(user.id, 1000001, [collection.id or 0]).item
    eat.set_notes("my note")
    eat.add_gloss(eat.senses[0].id or 0, "to scoff", "eng")
    entries.update(eat)
    water = importer.execute(user.id, 1000002, [collection.id or 0]).item
    water.deactivate()
    entries.update(water)
    return collection


def publish(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
    collection: EntryCollection,
    include_notes: bool = False,
) -> EntryCollection:
    return PublishEntryCollection(collections, entries).execute(
        user.id, collection.id or 0, include_notes
    )


def test_publish_snapshots_the_active_items_without_notes(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    published = publish(collections, entries, user, verbs)

    assert (published.is_public, published.published_version) == (True, 1)
    snapshot = collections.get_publication(published)
    assert snapshot is not None
    assert [i.source_entry_id for i in snapshot.items] == [1000001]
    assert snapshot.items[0].notes is None
    with_notes = publish(collections, entries, user, verbs, include_notes=True)
    assert with_notes.published_version == 2
    snapshot = collections.get_publication(with_notes)
    assert snapshot is not None and snapshot.items[0].notes == "my note"


def test_publishing_someone_elses_collection_fails(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    with pytest.raises(EntityNotFoundError):
        publish(collections, entries, other_user, verbs)


def test_import_public_records_the_download_and_the_source(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    publish(collections, entries, user, verbs)
    importer = ImportPublicEntryCollection(gateway, entries, collections)

    result = importer.execute(other_user.id, verbs.id or 0)

    copy = result.collection
    assert (copy.source_collection_id, copy.source_version) == (verbs.id, 1)
    eat = entries.get_by_source_entry_id(1000001, other_user.id)
    assert eat is not None
    own = [g for g in eat.senses[0].glosses if g.origin == "added"]
    assert [(g.text, g.source_collection_id) for g in own] == [("to scoff", verbs.id)]
    summary = collections.public_summary(verbs, other_user.id)
    assert (summary.downloads, summary.viewer_version) == (1, 1)
    # The owner's own import isn't a download.
    importer.execute(user.id, verbs.id or 0)
    assert collections.public_summary(verbs, user.id).downloads == 1


def test_a_private_collection_cant_be_imported(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    importer = ImportPublicEntryCollection(gateway, entries, collections)
    with pytest.raises(EntityNotFoundError):
        importer.execute(other_user.id, verbs.id or 0)

    publish(collections, entries, user, verbs)
    UnpublishEntryCollection(collections).execute(user.id, verbs.id or 0)
    with pytest.raises(EntityNotFoundError):
        importer.execute(other_user.id, verbs.id or 0)
    assert collections.find_public(PublicCollectionSearch(), user.id, 10, 0) == []


# --- Updating a copy from its source ---


def update(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    user: UserORM,
    copy: EntryCollection,
) -> CollectionUpdate[EntryCollection, int]:
    return UpdateEntryCollectionFromSource(gateway, entries, collections).execute(
        user.id, copy.id or 0
    )


def own_glosses(entry: PracticeEntry | None) -> list[str]:
    assert entry is not None
    return [g.text for s in entry.senses for g in s.glosses if g.origin == "added"]


@pytest.fixture
def copy(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> EntryCollection:
    """The other user's copy of verbs' v1 (食べる with "to scoff")."""
    publish(collections, entries, user, verbs)
    importer = ImportPublicEntryCollection(gateway, entries, collections)
    return importer.execute(other_user.id, verbs.id or 0).collection


def edit_scoff(
    entries: SqlAlchemyPracticeEntryRepository, user: UserORM, text: str
) -> None:
    eat = entries.get_by_source_entry_id(1000001, user.id)
    assert eat is not None
    gloss = next(g for s in eat.senses for g in s.glosses if g.origin == "added")
    eat.edit_gloss(gloss.id or 0, text)
    entries.update(eat)


def test_update_follows_what_the_source_changed(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    copy: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    edit_scoff(entries, user, "to wolf down")
    water = entries.get_by_source_entry_id(1000002, user.id)
    assert water is not None
    water.activate()
    entries.update(water)
    publish(collections, entries, user, verbs)
    assert collections.latest_source_versions(other_user.id) == {copy.id: 2}

    result = update(collections, entries, gateway, other_user, copy)

    assert (result.created, result.existing, result.removed) == (1, 1, 0)
    assert result.collection.source_version == 2
    summary = collections.public_summary(verbs, other_user.id)
    assert (summary.viewer_version, summary.downloads) == (2, 1)
    # The untouched "to scoff" follows the source: replaced by its new version.
    assert own_glosses(entries.get_by_source_entry_id(1000001, other_user.id)) == [
        "to wolf down"
    ]
    assert len(collections.source_item_ids(copy)) == 2
    again = update(collections, entries, gateway, other_user, copy)
    assert (again.created, again.existing, again.removed) == (0, 0, 0)


def test_update_keeps_what_the_user_touched_or_removed(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    copy: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    # The other user makes the meaning theirs, and takes 食べる out of the copy.
    edit_scoff(entries, other_user, "to gulp")
    eat = entries.get_by_source_entry_id(1000001, other_user.id)
    assert eat is not None
    RemoveEntryFromCollection(collections, entries).execute(
        other_user.id, copy.id or 0, eat.id or 0
    )
    edit_scoff(entries, user, "to wolf down")
    publish(collections, entries, user, verbs)

    result = update(collections, entries, gateway, other_user, copy)

    assert result.created == 0 and collections.source_item_ids(copy) == set()
    # Dismissed: it isn't brought back, nor its parts merged.
    assert own_glosses(entries.get_by_source_entry_id(1000001, other_user.id)) == [
        "to gulp"
    ]


def test_dropped_items_leave_the_collection_not_the_library(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    copy: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    eat = entries.get_by_source_entry_id(1000001, user.id)
    assert eat is not None
    RemoveEntryFromCollection(collections, entries).execute(
        user.id, verbs.id or 0, eat.id or 0
    )
    publish(collections, entries, user, verbs)

    result = update(collections, entries, gateway, other_user, copy)

    assert result.removed == 1
    assert collections.source_item_ids(copy) == set()
    assert entries.get_by_source_entry_id(1000001, other_user.id) is not None


def test_updating_needs_a_public_source(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    copy: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    UnpublishEntryCollection(collections).execute(user.id, verbs.id or 0)
    assert collections.latest_source_versions(other_user.id) == {}
    with pytest.raises(EntityNotFoundError):
        update(collections, entries, gateway, other_user, copy)
    with pytest.raises(EntityNotFoundError):  # a collection that isn't a copy
        update(collections, entries, gateway, user, verbs)
