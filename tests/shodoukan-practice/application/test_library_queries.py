from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import ImportEntry, ImportKanji
from shodoukan_practice.application.queries import GetImportStatus
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
