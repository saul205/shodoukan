import pytest
from factories import USER_ID, make_entry, sudachi
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands.dictionary_sentences import (
    add_dictionary_sentences,
)
from shodoukan_practice.domain.entities import PracticeEntry, SentenceTranslation
from shodoukan_practice.domain.gateways import (
    DictionaryEntry,
    DictionaryExample,
    DictionaryExampleSentence,
    DictionarySense,
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


def example(japanese: str, form: str, english: str | None = None) -> DictionaryExample:
    return DictionaryExample(
        text=form,
        sentences=[
            DictionaryExampleSentence(lang="jpn", text=japanese),
            *([DictionaryExampleSentence(lang="eng", text=english)] if english else []),
        ],
    )


def dictionary_entry(*senses: list[DictionaryExample]) -> DictionaryEntry:
    """The dictionary entry behind `make_entry`: its senses' examples."""
    return DictionaryEntry(
        id=1000001,
        kanji_readings=[],
        readings=[],
        senses=[
            DictionarySense(
                pos=[],
                misc=[],
                dialects=[],
                info=[],
                glosses=[],
                cross_references=[],
                examples=examples,
            )
            for examples in senses
        ],
        jlpt=None,
        is_common=False,
    )


def add(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    entry: PracticeEntry,
    dictionary: DictionaryEntry,
) -> None:
    add_dictionary_sentences(
        sentences,
        SqlAlchemyPracticeEntryRepository(session),
        sudachi(),
        entry,
        [sense.examples for sense in dictionary.senses],
    )


def test_the_examples_become_linked_analyzed_sentences(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    user: UserORM,
) -> None:
    entry = store(session, make_entry(USER_ID))

    add(session, sentences, entry, dictionary_entry([example(RICE, "食べる", "Eat.")]))

    [sentence] = sentences.for_entry(entry.id or 0, USER_ID)
    [word] = sentence.words
    assert sentence.text == RICE
    assert sentence.origin == "imported"
    assert sentence.translations == [SentenceTranslation(lang="eng", text="Eat.")]
    assert sentence.surface(word) == "食べる"
    assert (word.entry_id, word.sense_id) == (entry.id, entry.senses[0].id)
    # Analyzed when stored, so it can be asked at once.
    assert (word.lemma, word.reading) == ("食べる", "たべる")


def test_a_sentence_of_another_word_is_reused(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    user: UserORM,
) -> None:
    first = store(session, make_entry(USER_ID))
    add(session, sentences, first, dictionary_entry([example(RICE, "食べる")]))
    second = store(session, make_entry(USER_ID, source_entry_id=1000002))

    add(
        session,
        sentences,
        second,
        dictionary_entry([example(RICE, "ご飯")], [example("ご飯が好き。", "ご飯")]),
    )

    shared, own = sentences.for_entry(second.id or 0, USER_ID)
    assert sentences.for_entry(first.id or 0, USER_ID) == [shared]
    assert [(shared.surface(w), w.entry_id) for w in shared.words] == [
        ("食べる", first.id),
        ("ご飯", second.id),
    ]
    assert own.text == "ご飯が好き。"
    assert [w.sense_id for w in own.words] == [second.senses[1].id]


def test_a_sentence_under_two_senses_is_stored_once(
    session: Session,
    sentences: SqlAlchemyPracticeSentenceRepository,
    user: UserORM,
) -> None:
    entry = store(session, make_entry(USER_ID))

    add(
        session,
        sentences,
        entry,
        dictionary_entry([example(RICE, "食べる")], [example(RICE, "食べる")]),
    )

    [sentence] = sentences.for_entry(entry.id or 0, USER_ID)
    assert [w.sense_id for w in sentence.words] == [entry.senses[0].id]


def test_the_entry_must_be_stored(
    session: Session, sentences: SqlAlchemyPracticeSentenceRepository
) -> None:
    with pytest.raises(ValueError):
        add(session, sentences, make_entry(USER_ID), dictionary_entry())
