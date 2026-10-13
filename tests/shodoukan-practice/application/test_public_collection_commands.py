import pytest
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import (
    CreateEntryCollection,
    ImportEntry,
    ImportPublicEntryCollection,
    PublishEntryCollection,
    UnpublishEntryCollection,
)
from shodoukan_practice.domain.entities import EntryCollection
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
