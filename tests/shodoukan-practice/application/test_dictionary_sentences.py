import pytest
from factories import USER_ID, make_entry
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands.dictionary_sentences import (
    add_dictionary_sentences,
)
from shodoukan_practice.domain.entities import (
    PracticeEntry,
    PracticeExample,
    PracticeExampleSentence,
    SentenceTranslation,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeSentenceRepository,
)

RICE = "ご飯を食べる。"


@pytest.fixture
def sentences(session: Session) -> SqlAlchemyPracticeSentenceRepository:
    return SqlAlchemyPracticeSentenceRepository(session)


def store(session: Session, entry: PracticeEntry) -> PracticeEntry:
    return SqlAlchemyPracticeEntryRepository(session).add(entry)


def example(japanese: str, form: str) -> PracticeExample:
    return PracticeExample(
        id=None,
        text=form,
        sentences=[PracticeExampleSentence(lang="jpn", text=japanese)],
    )


def eat(session: Session) -> PracticeEntry:
    entry = make_entry(USER_ID)
    entry.senses[0].examples[0].text = "食べる"
    return store(session, entry)


def test_the_examples_become_linked_sentences(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    user: UserORM,
) -> None:
    entry = eat(session)

    add_dictionary_sentences(sentences, entry)

    [sentence] = sentences.for_entry(entry.id or 0, USER_ID)
    [word] = sentence.words
    assert sentence.text == RICE
    assert sentence.origin == "imported"
    assert sentence.translations == [SentenceTranslation(lang="eng", text="Eat rice.")]
    assert sentence.surface(word) == "食べる"
    assert (word.entry_id, word.sense_id) == (entry.id, entry.senses[0].id)


def test_a_sentence_of_another_word_is_reused(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    user: UserORM,
) -> None:
    first = eat(session)
    add_dictionary_sentences(sentences, first)
    rice = make_entry(USER_ID, source_entry_id=1000002)
    rice.senses[0].examples = [example(RICE, "ご飯")]
    rice.senses[1].examples = [example("ご飯が好き。", "ご飯")]
    second = store(session, rice)

    add_dictionary_sentences(sentences, second)

    shared, own = sentences.for_entry(second.id or 0, USER_ID)
    assert sentences.for_entry(first.id or 0, USER_ID) == [shared]
    assert [(shared.surface(w), w.entry_id) for w in shared.words] == [
        ("食べる", first.id),
        ("ご飯", second.id),
    ]
    assert own.text == "ご飯が好き。"
    assert len(sentences.imported_by_text([RICE, "ご飯が好き。"], USER_ID)) == 2


def test_a_sentence_under_two_senses_is_stored_once(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    user: UserORM,
) -> None:
    entry = make_entry(USER_ID)
    entry.senses[1].examples = [example(RICE, "食べる")]
    stored = store(session, entry)

    add_dictionary_sentences(sentences, stored)

    [sentence] = sentences.for_entry(stored.id or 0, USER_ID)
    assert [w.sense_id for w in sentence.words] == [stored.senses[0].id]


def test_the_entry_must_be_stored(
    sentences: SqlAlchemyPracticeSentenceRepository,
) -> None:
    with pytest.raises(ValueError):
        add_dictionary_sentences(sentences, make_entry(USER_ID))
