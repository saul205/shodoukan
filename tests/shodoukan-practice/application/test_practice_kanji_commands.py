import pytest
from factories import make_kanji
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import (
    AddKanjiMeaning,
    EditKanjiMeaning,
    RemoveKanjiFromLibrary,
    RemoveKanjiMeaning,
    SetKanjiActive,
    SetKanjiNotes,
    SetKanjiPartEnabled,
)
from shodoukan_practice.domain.entities import PracticeKanji
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    OriginalDataError,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyPracticeKanjiRepository:
    return SqlAlchemyPracticeKanjiRepository(session)


@pytest.fixture
def kanji(repo: SqlAlchemyPracticeKanjiRepository, user: UserORM) -> PracticeKanji:
    return repo.add(make_kanji(user.id))


def test_notes_active_and_enabled(
    repo: SqlAlchemyPracticeKanjiRepository, kanji: PracticeKanji, user: UserORM
) -> None:
    assert kanji.id and kanji.kun_readings[0].id
    kanji_id, kun_id = kanji.id, kanji.kun_readings[0].id

    SetKanjiNotes(repo).execute(user.id, kanji_id, "radical 食")
    SetKanjiActive(repo).execute(user.id, kanji_id, False)
    result = SetKanjiPartEnabled(repo).execute(
        user.id, kanji_id, "readings", kun_id, False
    )

    assert result.notes == "radical 食"
    assert result.is_active is False
    assert result.kun_readings[0].enabled is False
    assert repo.get(kanji_id, user.id) == result


def test_own_meanings_lifecycle(
    repo: SqlAlchemyPracticeKanjiRepository, kanji: PracticeKanji, user: UserORM
) -> None:
    assert kanji.id is not None
    added = AddKanjiMeaning(repo).execute(user.id, kanji.id, "meal", "en")
    meaning = added.meanings[-1]
    assert meaning.id is not None and meaning.origin == "added"

    edited = EditKanjiMeaning(repo).execute(user.id, kanji.id, meaning.id, "dish")
    assert edited.meanings[-1].text == "dish"
    removed = RemoveKanjiMeaning(repo).execute(user.id, kanji.id, meaning.id)
    assert "dish" not in [m.text for m in removed.meanings]


def test_dictionary_meanings_cant_be_changed(
    repo: SqlAlchemyPracticeKanjiRepository, kanji: PracticeKanji, user: UserORM
) -> None:
    assert kanji.id and kanji.meanings[0].id
    with pytest.raises(OriginalDataError):
        EditKanjiMeaning(repo).execute(user.id, kanji.id, kanji.meanings[0].id, "x")
    with pytest.raises(OriginalDataError):
        RemoveKanjiMeaning(repo).execute(user.id, kanji.id, kanji.meanings[0].id)


def test_remove_from_library(
    repo: SqlAlchemyPracticeKanjiRepository,
    kanji: PracticeKanji,
    user: UserORM,
    other_user: UserORM,
) -> None:
    assert kanji.id is not None
    with pytest.raises(EntityNotFoundError):
        RemoveKanjiFromLibrary(repo).execute(other_user.id, kanji.id)

    RemoveKanjiFromLibrary(repo).execute(user.id, kanji.id)

    assert repo.get(kanji.id, user.id) is None
