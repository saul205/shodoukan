import pytest
from factories import (
    make_entry,
    make_entry_collection,
    make_kanji,
    make_kanji_collection,
)
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import ImportEntry, ImportKanji
from shodoukan_practice.application.queries import (
    GetImportStatus,
    GetLibraryEntry,
    GetLibraryKanji,
    ListCollectionsOfEntry,
    ListCollectionsOfKanji,
)
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)


def test_status_lists_only_imported_items(
    session: Session, dictionary: Dictionary, user: UserORM, other_user: UserORM
) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)
    entries = SqlAlchemyPracticeEntryRepository(session)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    import_entry = ImportEntry(
        gateway, entries, SqlAlchemyEntryCollectionRepository(session)
    )
    import_kanji = ImportKanji(
        gateway, kanji, SqlAlchemyKanjiCollectionRepository(session)
    )
    entry = import_entry.execute(user.id, 1000001).item
    食 = import_kanji.execute(user.id, "食").item
    import_entry.execute(other_user.id, 1000002)

    status = GetImportStatus(entries, kanji).execute(
        user.id, [1000001, 1000002, 1000001], ["食", "水"]
    )

    assert status.entries == {1000001: entry.id}
    assert status.kanji == {"食": 食.id}


def test_status_of_nothing_is_empty(session: Session, user: UserORM) -> None:
    status = GetImportStatus(
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    ).execute(user.id, [], [])

    assert status.entries == {}
    assert status.kanji == {}


def test_get_library_items_are_scoped_to_the_user(
    session: Session, user: UserORM, other_user: UserORM
) -> None:
    entries = SqlAlchemyPracticeEntryRepository(session)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    entry = entries.add(make_entry(user.id))
    item = kanji.add(make_kanji(user.id))
    assert entry.id is not None and item.id is not None

    assert GetLibraryEntry(entries).execute(user.id, entry.id) == entry
    assert GetLibraryKanji(kanji).execute(user.id, item.id) == item
    with pytest.raises(EntityNotFoundError):
        GetLibraryEntry(entries).execute(other_user.id, entry.id)
    with pytest.raises(EntityNotFoundError):
        GetLibraryKanji(kanji).execute(other_user.id, item.id)


def test_collections_of_an_item(session: Session, user: UserORM) -> None:
    entries = SqlAlchemyPracticeEntryRepository(session)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    entry_collections = SqlAlchemyEntryCollectionRepository(session)
    kanji_collections = SqlAlchemyKanjiCollectionRepository(session)
    entry = entries.add(make_entry(user.id))
    item = kanji.add(make_kanji(user.id))
    verbs = entry_collections.add(make_entry_collection(user.id, "verbs"))
    n5 = kanji_collections.add(make_kanji_collection(user.id, "N5"))
    entry_collections.add_item(verbs, entry)
    kanji_collections.add_item(n5, item)
    assert entry.id is not None and item.id is not None

    of_entry = ListCollectionsOfEntry(entries, entry_collections)
    of_kanji = ListCollectionsOfKanji(kanji, kanji_collections)

    assert of_entry.execute(user.id, entry.id) == [verbs]
    assert of_kanji.execute(user.id, item.id) == [n5]
