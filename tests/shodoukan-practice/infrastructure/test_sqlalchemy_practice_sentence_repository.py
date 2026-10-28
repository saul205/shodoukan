import pytest
from factories import OTHER_USER_ID, USER_ID, make_entry
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import (
    Inflection,
    PracticeEntry,
    PracticeSentence,
    SentenceTranslation,
)
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeSentenceRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyPracticeSentenceRepository:
    return SqlAlchemyPracticeSentenceRepository(session)


@pytest.fixture
def entry(session: Session, user: UserORM) -> PracticeEntry:
    return SqlAlchemyPracticeEntryRepository(session).add(make_entry(USER_ID))


def dictionary_sentence(
    entry: PracticeEntry, text: str = "家に帰る。"
) -> PracticeSentence:
    assert entry.id is not None
    return PracticeSentence.from_dictionary(
        USER_ID,
        text,
        [SentenceTranslation(lang="eng", text="I go home.")],
        word="帰る",
        entry_id=entry.id,
        sense_id=entry.senses[0].id,
    )


def test_add_and_get(
    repo: SqlAlchemyPracticeSentenceRepository, entry: PracticeEntry
) -> None:
    stored = repo.add(dictionary_sentence(entry))

    assert stored.id is not None
    assert stored.words[0].id is not None
    assert repo.get(stored.id, USER_ID) == stored


def test_get_is_scoped_to_the_user(
    repo: SqlAlchemyPracticeSentenceRepository,
    entry: PracticeEntry,
    other_user: UserORM,
) -> None:
    stored = repo.add(dictionary_sentence(entry))
    assert stored.id is not None

    assert repo.get(stored.id, OTHER_USER_ID) is None
    assert repo.for_entry(entry.id or 0, OTHER_USER_ID) == []


def test_the_sentences_of_a_word(
    repo: SqlAlchemyPracticeSentenceRepository, entry: PracticeEntry
) -> None:
    first = repo.add(dictionary_sentence(entry))
    second = repo.add(dictionary_sentence(entry, "早く帰る。"))
    repo.add(PracticeSentence.create_own(USER_ID, "関係ない文。", None, "eng"))

    assert repo.for_entry(entry.id or 0, USER_ID) == [first, second]


def test_imported_by_text(
    repo: SqlAlchemyPracticeSentenceRepository, entry: PracticeEntry
) -> None:
    imported = repo.add(dictionary_sentence(entry))
    repo.add(PracticeSentence.create_own(USER_ID, "早く帰る。", None, "eng"))

    found = repo.imported_by_text(["家に帰る。", "早く帰る。", "ない。"], USER_ID)

    assert found == {"家に帰る。": imported}  # own sentences aren't reused
    assert repo.imported_by_text([], USER_ID) == {}


def test_update_words(
    repo: SqlAlchemyPracticeSentenceRepository, entry: PracticeEntry
) -> None:
    sentence = repo.add(dictionary_sentence(entry))
    word = sentence.words[0]
    assert word.id is not None
    sentence.analyze_word(
        word.id,
        "帰る",
        "カエル",
        ["動詞", "一般"],
        Inflection(endings=(), form="終止形"),
    )
    sentence.add_word(0, 1)  # 家
    sentence.set_notes("note")

    updated = repo.update(sentence)

    assert updated.words[0].lemma == "帰る"
    assert updated.words[0].inflection == Inflection(endings=(), form="終止形")
    assert updated.words[1].id is not None
    assert updated.notes == "note"
    assert updated.id is not None
    updated.remove_word(updated.words[0].id or 0)
    assert [w.start for w in repo.update(updated).words] == [0]
    assert repo.get(updated.id, USER_ID) == repo.update(updated)


def test_update_and_delete_require_the_users_row(
    repo: SqlAlchemyPracticeSentenceRepository,
    entry: PracticeEntry,
    other_user: UserORM,
) -> None:
    stored = repo.add(dictionary_sentence(entry))
    foreign = stored.model_copy(update={"user_id": OTHER_USER_ID})

    with pytest.raises(EntityNotFoundError):
        repo.update(foreign)
    with pytest.raises(EntityNotFoundError):
        repo.delete(foreign)
    repo.delete(stored)
    assert repo.get(stored.id or 0, USER_ID) is None


def test_removing_the_word_leaves_the_sentence_unlinked(
    session: Session,
    repo: SqlAlchemyPracticeSentenceRepository,
    entry: PracticeEntry,
) -> None:
    stored = repo.add(dictionary_sentence(entry))
    SqlAlchemyPracticeEntryRepository(session).delete(entry)
    session.expire_all()

    sentence = repo.get(stored.id or 0, USER_ID)

    assert sentence is not None
    assert (sentence.words[0].entry_id, sentence.words[0].sense_id) == (None, None)
    assert sentence.words[0].has_span


def test_needing_analysis(
    repo: SqlAlchemyPracticeSentenceRepository,
    entry: PracticeEntry,
    other_user: UserORM,
) -> None:
    gap = repo.add(dictionary_sentence(entry))
    unmarked = repo.add(
        PracticeSentence.from_dictionary(
            USER_ID, "帰宅した。", [], word="帰る", entry_id=entry.id, sense_id=None
        )
    )
    done = dictionary_sentence(entry, "早く帰る。")
    done.words[0].lemma = "帰る"
    repo.add(done)
    repo.add(PracticeSentence.create_own(USER_ID, "単語なし。", None, "eng"))

    assert repo.needing_analysis(USER_ID) == [gap, unmarked]
    assert repo.needing_analysis(OTHER_USER_ID) == []
    assert repo.users_needing_analysis() == [USER_ID]
