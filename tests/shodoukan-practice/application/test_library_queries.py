from factories import make_entry, make_kanji
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import ImportEntry, ImportKanji
from shodoukan_practice.application.queries import (
    GetImportStatus,
    ListLibraryEntries,
    ListLibraryKanji,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)


def test_status_lists_only_imported_items(
    session: Session, dictionary: Dictionary, user: UserORM, other_user: UserORM
) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)
    entries = SqlAlchemyPracticeEntryRepository(session)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    entry = ImportEntry(gateway, entries).execute(user.id, 1000001).item
    食 = ImportKanji(gateway, kanji).execute(user.id, "食").item
    ImportEntry(gateway, entries).execute(other_user.id, 1000002)

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


def test_list_library_entries_pages_with_a_total(
    session: Session, user: UserORM, other_user: UserORM
) -> None:
    entries = SqlAlchemyPracticeEntryRepository(session)
    first = entries.add(make_entry(user.id, 1))
    second = entries.add(make_entry(user.id, 2, is_active=False))
    entries.add(make_entry(other_user.id, 1))

    page = ListLibraryEntries(entries).execute(user.id, limit=1, offset=0)

    assert page.items == [second]
    assert (page.total, page.limit, page.offset) == (2, 1, 0)
    active = ListLibraryEntries(entries).execute(user.id, active=True)
    assert (active.items, active.total) == ([first], 1)


def test_list_library_kanji(session: Session, user: UserORM) -> None:
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    item = kanji.add(make_kanji(user.id))

    page = ListLibraryKanji(kanji).execute(user.id)

    assert (page.items, page.total) == ([item], 1)
