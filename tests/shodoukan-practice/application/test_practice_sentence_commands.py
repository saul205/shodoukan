import pytest
from factories import OTHER_USER_ID, USER_ID, make_entry
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import AnalyzeSentences
from shodoukan_practice.domain.entities import (
    Inflection,
    PracticeEntry,
    PracticeSentence,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.morphology import SudachiMorphologyGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeSentenceRepository,
)


@pytest.fixture(scope="module")
def morphology() -> SudachiMorphologyGateway:
    return SudachiMorphologyGateway()


@pytest.fixture
def sentences(session: Session) -> SqlAlchemyPracticeSentenceRepository:
    return SqlAlchemyPracticeSentenceRepository(session)


@pytest.fixture
def analyze(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    morphology: SudachiMorphologyGateway,
) -> AnalyzeSentences:
    return AnalyzeSentences(
        sentences, SqlAlchemyPracticeEntryRepository(session), morphology
    )


@pytest.fixture
def eat(session: Session, user: UserORM) -> PracticeEntry:
    """食べる (たべる, くう)."""
    return SqlAlchemyPracticeEntryRepository(session).add(make_entry(USER_ID))


def linked(text: str, entry: PracticeEntry, form: str = "") -> PracticeSentence:
    return PracticeSentence.from_dictionary(
        entry.user_id, text, [], word=form, entry_id=entry.id, sense_id=None
    )


def test_a_gap_is_analyzed(
    analyze: AnalyzeSentences,
    sentences: SqlAlchemyPracticeSentenceRepository,
    eat: PracticeEntry,
) -> None:
    stored = sentences.add(linked("ご飯を食べられた。", eat, form="食べられた"))

    result = analyze.execute()

    [word] = sentences.get(stored.id or 0, USER_ID).words  # type: ignore[union-attr]
    assert (result.users, result.sentences, result.analyzed) == (1, 1, 1)
    assert word.lemma == "食べる"
    assert word.reading == "たべられた"
    assert word.pos[0] == "動詞"
    assert word.inflection == Inflection(endings=("れる", "た"), form="終止形")


def test_a_linked_word_gets_its_gap(
    analyze: AnalyzeSentences,
    sentences: SqlAlchemyPracticeSentenceRepository,
    eat: PracticeEntry,
) -> None:
    # An own sentence: no form given, and 食べた isn't 食べる as written.
    stored = sentences.add(linked("昨日パンを食べた。", eat))

    result = analyze.execute()

    sentence = sentences.get(stored.id or 0, USER_ID)
    assert sentence is not None
    [word] = sentence.words
    assert (result.marked, result.analyzed, result.unmarked) == (1, 1, 0)
    assert sentence.surface(word) == "食べた"
    assert word.is_analyzed


def test_a_word_not_in_the_sentence_stays_without_a_gap(
    analyze: AnalyzeSentences,
    sentences: SqlAlchemyPracticeSentenceRepository,
    eat: PracticeEntry,
) -> None:
    sentences.add(linked("水を飲んだ。", eat))

    result = analyze.execute()

    assert (result.marked, result.unmarked) == (0, 1)


def test_what_the_user_corrected_is_kept(
    analyze: AnalyzeSentences,
    sentences: SqlAlchemyPracticeSentenceRepository,
    eat: PracticeEntry,
) -> None:
    stored = sentences.add(linked("ご飯を食べる。", eat, form="食べる"))
    analyze.execute()
    sentence = sentences.get(stored.id or 0, USER_ID)
    assert sentence is not None
    sentence.correct_word(sentence.words[0].id or 0, "食べる", "くう")
    sentences.update(sentence)

    again = analyze.execute()

    assert again.sentences == 0
    stored_again = sentences.get(stored.id or 0, USER_ID)
    assert stored_again is not None
    assert stored_again.words[0].reading == "くう"


def test_every_user_is_analyzed(
    session: Session,
    analyze: AnalyzeSentences,
    sentences: SqlAlchemyPracticeSentenceRepository,
    eat: PracticeEntry,
    other_user: UserORM,
) -> None:
    theirs = SqlAlchemyPracticeEntryRepository(session).add(make_entry(OTHER_USER_ID))
    sentences.add(linked("ご飯を食べる。", eat, form="食べる"))
    sentences.add(linked("パンを食べる。", theirs, form="食べる"))

    assert analyze.execute().users == 2
    assert sentences.needing_analysis(USER_ID) == []
    assert sentences.needing_analysis(OTHER_USER_ID) == []
