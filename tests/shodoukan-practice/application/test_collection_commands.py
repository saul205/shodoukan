import pytest
from factories import NOW, make_entry, make_kanji
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import (
    AddEntryToCollection,
    AddKanjiToCollection,
    CreateEntryCollection,
    CreateKanjiCollection,
    DeleteEntryCollection,
    DeleteKanjiCollection,
    RemoveEntryFromCollection,
    RemoveKanjiFromCollection,
    UpdateEntryCollection,
    UpdateKanjiCollection,
)
from shodoukan_practice.domain.entities import (
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeKanji,
)
from shodoukan_practice.domain.exceptions import (
    CollectionNameTakenError,
    EntityNotFoundError,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def collections(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def kanji_collections(session: Session) -> SqlAlchemyKanjiCollectionRepository:
    return SqlAlchemyKanjiCollectionRepository(session)


@pytest.fixture
def entries(session: Session) -> SqlAlchemyPracticeEntryRepository:
    return SqlAlchemyPracticeEntryRepository(session)


@pytest.fixture
def kanji(session: Session) -> SqlAlchemyPracticeKanjiRepository:
    return SqlAlchemyPracticeKanjiRepository(session)


@pytest.fixture
def verbs(
    collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> EntryCollection:
    return CreateEntryCollection(collections).execute(user.id, "verbs")


@pytest.fixture
def entry(entries: SqlAlchemyPracticeEntryRepository, user: UserORM) -> PracticeEntry:
    return entries.add(make_entry(user.id))


def _id(item: EntryCollection | KanjiCollection | PracticeEntry | PracticeKanji) -> int:
    assert item.id is not None
    return item.id


def test_create_stores_an_empty_collection(
    collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    created = CreateEntryCollection(collections).execute(
        user.id, "verbs", "Godan and ichidan"
    )

    assert created.description == "Godan and ichidan"
    assert collections.get(_id(created), user.id) == created
    assert collections.item_ids([created]) == set()


def test_create_with_a_taken_name_fails(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    with pytest.raises(CollectionNameTakenError):
        CreateEntryCollection(collections).execute(user.id, "verbs")


def test_entry_and_kanji_collections_may_share_a_name(
    kanji_collections: SqlAlchemyKanjiCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    created = CreateKanjiCollection(kanji_collections).execute(user.id, "verbs")
    assert created.name == "verbs"


def test_update_replaces_name_and_description(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    updated = UpdateEntryCollection(collections).execute(
        user.id, _id(verbs), "godan", "う-verbs"
    )

    assert (updated.name, updated.description) == ("godan", "う-verbs")
    assert updated.updated_at > verbs.updated_at
    assert collections.get(_id(verbs), user.id) == updated


def test_update_without_changes_keeps_updated_at(
    collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    created = collections.add(
        EntryCollection(
            id=None, user_id=user.id, name="verbs", created_at=NOW, updated_at=NOW
        )
    )
    updated = UpdateEntryCollection(collections).execute(
        user.id, _id(created), "verbs", None
    )
    assert updated.updated_at == NOW


def test_update_of_another_users_collection_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    with pytest.raises(EntityNotFoundError):
        UpdateEntryCollection(collections).execute(
            other_user.id, _id(verbs), "mine", None
        )


def test_update_to_a_taken_name_fails(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    nouns = CreateEntryCollection(collections).execute(user.id, "nouns")
    with pytest.raises(CollectionNameTakenError):
        UpdateEntryCollection(collections).execute(user.id, _id(nouns), "verbs", None)


def test_delete_keeps_the_items(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    entry: PracticeEntry,
    user: UserORM,
) -> None:
    AddEntryToCollection(collections, entries).execute(user.id, _id(verbs), _id(entry))
    DeleteEntryCollection(collections).execute(user.id, _id(verbs))

    assert collections.get(_id(verbs), user.id) is None
    assert entries.get(_id(entry), user.id) == entry


def test_delete_of_another_users_collection_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    with pytest.raises(EntityNotFoundError):
        DeleteEntryCollection(collections).execute(other_user.id, _id(verbs))


def test_add_and_remove_entry_are_idempotent(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    entry: PracticeEntry,
    user: UserORM,
) -> None:
    add = AddEntryToCollection(collections, entries)
    remove = RemoveEntryFromCollection(collections, entries)

    add.execute(user.id, _id(verbs), _id(entry))
    add.execute(user.id, _id(verbs), _id(entry))
    assert collections.item_ids([verbs]) == {_id(entry)}

    remove.execute(user.id, _id(verbs), _id(entry))
    remove.execute(user.id, _id(verbs), _id(entry))
    assert collections.item_ids([verbs]) == set()


def test_add_another_users_entry_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    theirs = entries.add(make_entry(other_user.id))
    with pytest.raises(EntityNotFoundError):
        AddEntryToCollection(collections, entries).execute(
            user.id, _id(verbs), _id(theirs)
        )


def test_add_to_another_users_collection_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    theirs = entries.add(make_entry(other_user.id))
    with pytest.raises(EntityNotFoundError):
        AddEntryToCollection(collections, entries).execute(
            other_user.id, _id(verbs), _id(theirs)
        )


def test_kanji_collection_lifecycle(
    kanji_collections: SqlAlchemyKanjiCollectionRepository,
    kanji: SqlAlchemyPracticeKanjiRepository,
    user: UserORM,
) -> None:
    item = kanji.add(make_kanji(user.id))
    n5 = CreateKanjiCollection(kanji_collections).execute(user.id, "N5")

    AddKanjiToCollection(kanji_collections, kanji).execute(user.id, _id(n5), _id(item))
    assert kanji_collections.item_ids([n5]) == {_id(item)}

    renamed = UpdateKanjiCollection(kanji_collections).execute(
        user.id, _id(n5), "JLPT N5", None
    )
    assert renamed.name == "JLPT N5"

    RemoveKanjiFromCollection(kanji_collections, kanji).execute(
        user.id, _id(n5), _id(item)
    )
    assert kanji_collections.item_ids([n5]) == set()

    DeleteKanjiCollection(kanji_collections).execute(user.id, _id(n5))
    assert kanji_collections.get(_id(n5), user.id) is None
    with pytest.raises(EntityNotFoundError):
        AddKanjiToCollection(kanji_collections, kanji).execute(
            user.id, _id(n5), _id(item)
        )
