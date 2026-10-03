import pytest
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import ImportEntry, ImportKanji
from shodoukan_practice.domain.exceptions import DictionaryItemNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def import_entry(session: Session, dictionary: Dictionary) -> ImportEntry:
    return ImportEntry(
        ShodoukanDictionaryGateway(dictionary),
        SqlAlchemyPracticeEntryRepository(session),
    )


@pytest.fixture
def import_kanji(session: Session, dictionary: Dictionary) -> ImportKanji:
    return ImportKanji(
        ShodoukanDictionaryGateway(dictionary),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def test_import_entry_adds_it_to_the_library(
    import_entry: ImportEntry, user: UserORM, session: Session
) -> None:
    result = import_entry.execute(user.id, 1000001)

    assert result.created is True
    assert result.item.id is not None
    assert result.item.source_entry_id == 1000001
    stored = SqlAlchemyPracticeEntryRepository(session).get(result.item.id, user.id)
    assert stored == result.item


def test_import_entry_twice_returns_the_existing_copy(
    import_entry: ImportEntry, user: UserORM
) -> None:
    first = import_entry.execute(user.id, 1000001)
    again = import_entry.execute(user.id, 1000001)

    assert again.created is False
    assert again.item == first.item


def test_each_user_gets_their_own_copy(
    import_entry: ImportEntry, user: UserORM, other_user: UserORM
) -> None:
    mine = import_entry.execute(user.id, 1000001)
    theirs = import_entry.execute(other_user.id, 1000001)

    assert theirs.created is True
    assert theirs.item.id != mine.item.id
    assert theirs.item.user_id == other_user.id


def test_import_unknown_entry_fails(import_entry: ImportEntry, user: UserORM) -> None:
    with pytest.raises(DictionaryItemNotFoundError):
        import_entry.execute(user.id, 999)


def test_import_kanji_adds_it_then_returns_the_existing_copy(
    import_kanji: ImportKanji, user: UserORM
) -> None:
    first = import_kanji.execute(user.id, "食")
    again = import_kanji.execute(user.id, "食")

    assert first.created is True
    assert first.item.literal == "食"
    assert [m.text for m in first.item.meanings] == ["eat", "food"]
    assert again.created is False
    assert again.item == first.item


def test_import_unknown_kanji_fails(import_kanji: ImportKanji, user: UserORM) -> None:
    with pytest.raises(DictionaryItemNotFoundError):
        import_kanji.execute(user.id, "龘")
