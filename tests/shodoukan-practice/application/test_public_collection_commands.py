import pytest
from factories import sudachi
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import (
    AddSentence,
    CollectionUpdate,
    CreateEntryCollection,
    ImportEntry,
    ImportPublicEntryCollection,
    PublishEntryCollection,
    RemoveEntryFromCollection,
    RemoveEntryFromLibrary,
    RemoveSentence,
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
    SqlAlchemyPracticeSentenceRepository,
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
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    user: UserORM,
) -> EntryCollection:
    """The user's "verbs": 食べる (with a note and their own meaning) and 水,
    which they deactivated."""
    collection = CreateEntryCollection(collections).execute(user.id, "verbs")
    importer = ImportEntry(
        gateway,
        entries,
        collections,
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    )
    eat = importer.execute(user.id, 1000001, [collection.id or 0]).item
    eat.set_notes("my note")
    eat.add_gloss(eat.senses[0].id or 0, "to scoff", "eng")
    entries.update(eat)
    water = importer.execute(user.id, 1000002, [collection.id or 0]).item
    water.deactivate()
    entries.update(water)
    return collection


def publish(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
    collection: EntryCollection,
    include_notes: bool = False,
) -> EntryCollection:
    return PublishEntryCollection(
        collections, entries, SqlAlchemyPracticeSentenceRepository(session)
    ).execute(user.id, collection.id or 0, include_notes)


def test_publish_snapshots_the_active_items_without_notes(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    published = publish(session, collections, entries, user, verbs)

    assert (published.is_public, published.published_version) == (True, 1)
    snapshot = collections.get_publication(published)
    assert snapshot is not None
    assert [i.source_entry_id for i in snapshot.items] == [1000001]
    assert snapshot.items[0].notes is None
    with_notes = publish(session, collections, entries, user, verbs, include_notes=True)
    assert with_notes.published_version == 2
    snapshot = collections.get_publication(with_notes)
    assert snapshot is not None and snapshot.items[0].notes == "my note"


def test_publishing_someone_elses_collection_fails(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    with pytest.raises(EntityNotFoundError):
        publish(session, collections, entries, other_user, verbs)


def test_import_public_records_the_download_and_the_source(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    publish(session, collections, entries, user, verbs)
    importer = ImportPublicEntryCollection(
        gateway,
        entries,
        collections,
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    )

    result = importer.execute(other_user.id, verbs.id or 0)

    copy = result.collection
    assert (copy.source_collection_id, copy.source_version) == (verbs.id, 1)
    eat = entries.get_by_source_entry_id(1000001, other_user.id)
    assert eat is not None
    own = [g for g in eat.senses[0].glosses if g.origin == "added"]
    assert [(g.text, g.source_collection_ids) for g in own] == [
        ("to scoff", [verbs.id])
    ]
    summary = collections.public_summary(verbs, other_user.id)
    assert (summary.downloads, summary.viewer_version) == (1, 1)
    # The owner's own import isn't a download.
    importer.execute(user.id, verbs.id or 0)
    assert collections.public_summary(verbs, user.id).downloads == 1


def test_a_private_collection_cant_be_imported(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    importer = ImportPublicEntryCollection(
        gateway,
        entries,
        collections,
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    )
    with pytest.raises(EntityNotFoundError):
        importer.execute(other_user.id, verbs.id or 0)

    publish(session, collections, entries, user, verbs)
    UnpublishEntryCollection(collections).execute(user.id, verbs.id or 0)
    with pytest.raises(EntityNotFoundError):
        importer.execute(other_user.id, verbs.id or 0)
    assert collections.find_public(PublicCollectionSearch(), user.id, 10, 0) == []


# --- Updating a copy from its source ---


def update(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    user: UserORM,
    copy: EntryCollection,
) -> CollectionUpdate[EntryCollection, int]:
    return UpdateEntryCollectionFromSource(
        gateway,
        entries,
        collections,
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    ).execute(user.id, copy.id or 0)


def own_glosses(entry: PracticeEntry | None) -> list[str]:
    assert entry is not None
    return [g.text for s in entry.senses for g in s.glosses if g.origin == "added"]


@pytest.fixture
def copy(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> EntryCollection:
    """The other user's copy of verbs' v1 (食べる with "to scoff")."""
    publish(session, collections, entries, user, verbs)
    importer = ImportPublicEntryCollection(
        gateway,
        entries,
        collections,
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    )
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
    session: Session,
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
    publish(session, collections, entries, user, verbs)
    assert collections.latest_source_versions(other_user.id) == {copy.id: 2}

    result = update(session, collections, entries, gateway, other_user, copy)

    assert (result.created, result.existing, result.removed) == (1, 1, 0)
    assert result.collection.source_version == 2
    summary = collections.public_summary(verbs, other_user.id)
    assert (summary.viewer_version, summary.downloads) == (2, 1)
    # The untouched "to scoff" follows the source: replaced by its new version.
    assert own_glosses(entries.get_by_source_entry_id(1000001, other_user.id)) == [
        "to wolf down"
    ]
    assert len(collections.source_item_ids(copy)) == 2
    again = update(session, collections, entries, gateway, other_user, copy)
    assert (again.created, again.existing, again.removed) == (0, 0, 0)


def test_update_keeps_what_the_user_touched_or_removed(
    session: Session,
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
    publish(session, collections, entries, user, verbs)

    result = update(session, collections, entries, gateway, other_user, copy)

    assert result.created == 0 and collections.source_item_ids(copy) == set()
    # Dismissed: it isn't brought back, nor its parts merged.
    assert own_glosses(entries.get_by_source_entry_id(1000001, other_user.id)) == [
        "to gulp"
    ]


def test_dropped_items_leave_the_collection_not_the_library(
    session: Session,
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
    publish(session, collections, entries, user, verbs)

    result = update(session, collections, entries, gateway, other_user, copy)

    assert result.removed == 1
    assert collections.source_item_ids(copy) == set()
    assert entries.get_by_source_entry_id(1000001, other_user.id) is not None


def test_updating_needs_a_public_source(
    session: Session,
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
        update(session, collections, entries, gateway, other_user, copy)
    with pytest.raises(EntityNotFoundError):  # a collection that isn't a copy
        update(session, collections, entries, gateway, user, verbs)


def test_a_word_deleted_from_the_library_doesnt_come_back(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    copy: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    eat = entries.get_by_source_entry_id(1000001, other_user.id)
    assert eat is not None
    RemoveEntryFromLibrary(entries, collections).execute(other_user.id, eat.id or 0)
    edit_scoff(entries, user, "to wolf down")
    publish(session, collections, entries, user, verbs)

    result = update(session, collections, entries, gateway, other_user, copy)

    assert result.created == 0
    assert entries.get_by_source_entry_id(1000001, other_user.id) is None


def test_putting_a_dismissed_word_back_lets_the_source_follow_it(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    copy: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    eat = entries.get_by_source_entry_id(1000001, other_user.id)
    assert eat is not None
    RemoveEntryFromLibrary(entries, collections).execute(other_user.id, eat.id or 0)
    assert collections.dismissed_items(copy) == {"entry:1000001"}

    # Imported again from the dictionary, straight into the copy.
    again = ImportEntry(
        gateway,
        entries,
        collections,
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    ).execute(other_user.id, 1000001, [copy.id or 0])
    assert collections.dismissed_items(copy) == set()
    assert collections.is_from_source(copy, again.item)
    edit_scoff(entries, user, "to wolf down")
    publish(session, collections, entries, user, verbs)

    update(session, collections, entries, gateway, other_user, copy)

    assert own_glosses(entries.get_by_source_entry_id(1000001, other_user.id)) == [
        "to wolf down"
    ]


def test_an_update_lets_go_of_a_sentence_the_source_dropped(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    sentences = SqlAlchemyPracticeSentenceRepository(session)
    eat = entries.get_by_source_entry_id(1000001, user.id)
    assert eat is not None
    add = AddSentence(sentences, entries, sudachi())
    dropped = add.execute(user.id, "パンを食べた。", None, "eng", entry_id=eat.id)
    add.execute(user.id, "肉を食べた。", None, "eng", entry_id=eat.id)
    publish(session, collections, entries, user, verbs)
    copy = (
        ImportPublicEntryCollection(gateway, entries, collections, sentences, sudachi())
        .execute(other_user.id, verbs.id or 0)
        .collection
    )
    theirs = entries.get_by_source_entry_id(1000001, other_user.id)
    assert theirs is not None
    assert len(sentences.for_entry(theirs.id or 0, other_user.id)) == 2

    RemoveSentence(sentences, entries, sudachi()).execute(user.id, dropped.id or 0)
    publish(session, collections, entries, user, verbs)
    update(session, collections, entries, gateway, other_user, copy)

    [kept] = sentences.for_entry(theirs.id or 0, other_user.id)
    assert kept.text == "肉を食べた。"


def test_a_copied_sentence_the_user_removed_isnt_brought_back(
    session: Session,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    gateway: ShodoukanDictionaryGateway,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    sentences = SqlAlchemyPracticeSentenceRepository(session)
    eat = entries.get_by_source_entry_id(1000001, user.id)
    assert eat is not None
    AddSentence(sentences, entries, sudachi()).execute(
        user.id, "パンを食べた。", None, "eng", entry_id=eat.id
    )
    publish(session, collections, entries, user, verbs)
    copy = (
        ImportPublicEntryCollection(gateway, entries, collections, sentences, sudachi())
        .execute(other_user.id, verbs.id or 0)
        .collection
    )
    theirs = entries.get_by_source_entry_id(1000001, other_user.id)
    assert theirs is not None
    [copied] = sentences.for_entry(theirs.id or 0, other_user.id)

    RemoveSentence(sentences, entries, sudachi()).execute(other_user.id, copied.id or 0)
    eat.set_notes("a new version")
    entries.update(eat)
    publish(session, collections, entries, user, verbs)
    update(session, collections, entries, gateway, other_user, copy)

    assert sentences.for_entry(theirs.id or 0, other_user.id) == []
