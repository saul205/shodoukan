from random import Random

import pytest
from factories import choice_settings, make_kanji_collection, make_kanji_with, make_word
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import (
    AnswerExerciseQuestion,
    CreateExercise,
    StartExerciseSession,
)
from shodoukan_practice.application.queries import GetExerciseSession
from shodoukan_practice.domain.entities import (
    EntryCollection,
    Exercise,
    KanjiCollection,
    OptionAnswer,
)
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    ExercisePoolTooSmallError,
    InvalidAnswerError,
    QuestionAnsweredError,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)

KANJI = [
    ("食", "ショク", "た.べる", "eat"),
    ("水", "スイ", "みず", "water"),
    ("火", "カ", "ひ", "fire"),
    ("木", "モク", "き", "tree"),
    ("山", "サン", "やま", "mountain"),
]


@pytest.fixture
def start(session: Session) -> StartExerciseSession:
    return StartExerciseSession(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyExerciseSessionRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
        Random(7),
    )


@pytest.fixture
def answer(session: Session) -> AnswerExerciseQuestion:
    return AnswerExerciseQuestion(SqlAlchemyExerciseSessionRepository(session))


@pytest.fixture
def n5(session: Session, user: UserORM) -> KanjiCollection:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    collection = collections.add(make_kanji_collection(user.id, "N5"))
    for literal, on, kun, meaning in KANJI:
        item = kanji.add(
            make_kanji_with(
                user.id, literal, on=[on], kun=[kun], meanings=[(meaning, "en")]
            )
        )
        collections.add_item(collection, item)
    return collection


def _exercise(
    session: Session, user: UserORM, collection: KanjiCollection, **settings: object
) -> Exercise:
    assert collection.id is not None
    return CreateExercise(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    ).execute(
        user.id,
        "kanji",
        "N5",
        None,
        [collection.id],
        choice_settings((("literal",), "kunyomi"), back_fields=["meaning"], **settings),
    )


def test_start_builds_and_stores_the_questions(
    session: Session,
    start: StartExerciseSession,
    user: UserORM,
    n5: KanjiCollection,
) -> None:
    exercise = _exercise(session, user, n5, question_count=3)
    assert exercise.id is not None

    started = start.execute(user.id, exercise.id, "en")

    assert started.id is not None
    assert started.exercise_id == exercise.id
    assert started.exercise_name == "N5"
    assert started.item_kind == "kanji"
    assert len(started.questions) == 3
    assert all(q.id is not None and len(q.options) == 4 for q in started.questions)
    assert started.finished_at is None
    got = GetExerciseSession(SqlAlchemyExerciseSessionRepository(session))
    assert got.execute(user.id, started.id) == started


def test_inactive_items_are_left_out(
    session: Session,
    start: StartExerciseSession,
    user: UserORM,
    n5: KanjiCollection,
) -> None:
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    for item in kanji.get_many(range(1, 100), user.id):
        if item.literal != "食":
            item.deactivate()
            kanji.update(item)
    exercise = _exercise(session, user, n5)
    assert exercise.id is not None
    with pytest.raises(ExercisePoolTooSmallError):
        start.execute(user.id, exercise.id, "en")


def test_exercise_without_collections_cant_start(
    session: Session,
    start: StartExerciseSession,
    user: UserORM,
    n5: KanjiCollection,
) -> None:
    exercise = _exercise(session, user, n5)
    SqlAlchemyKanjiCollectionRepository(session).delete(n5)
    session.expire_all()
    assert exercise.id is not None
    with pytest.raises(ExercisePoolTooSmallError):
        start.execute(user.id, exercise.id, "en")


def test_unknown_or_foreign_exercise(
    session: Session,
    start: StartExerciseSession,
    user: UserORM,
    other_user: UserORM,
    n5: KanjiCollection,
) -> None:
    exercise = _exercise(session, user, n5)
    assert exercise.id is not None
    with pytest.raises(EntityNotFoundError):
        start.execute(other_user.id, exercise.id, "en")
    with pytest.raises(EntityNotFoundError):
        start.execute(user.id, exercise.id + 1, "en")


def test_entry_exercise_uses_the_gloss_language(
    session: Session, start: StartExerciseSession, user: UserORM
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    entries = SqlAlchemyPracticeEntryRepository(session)
    verbs: EntryCollection = collections.add(
        EntryCollection(id=None, user_id=user.id, name="verbs")
    )
    for i, (writing, reading, meaning) in enumerate(
        [
            ("食べる", "たべる", "comer"),
            ("飲む", "のむ", "beber"),
            ("見る", "みる", "ver"),
        ]
    ):
        entry = entries.add(
            make_word(user.id, i + 1, writing, reading, [(meaning, "spa")])
        )
        collections.add_item(verbs, entry)
    assert verbs.id is not None
    exercise = CreateExercise(
        SqlAlchemyExerciseRepository(session),
        collections,
        SqlAlchemyKanjiCollectionRepository(session),
    ).execute(
        user.id,
        "entries",
        "Verbs",
        None,
        [verbs.id],
        choice_settings((("meaning",), "writing")),
    )
    assert exercise.id is not None

    with pytest.raises(ExercisePoolTooSmallError):  # no English meanings
        start.execute(user.id, exercise.id, "eng")
    started = start.execute(user.id, exercise.id, "spa")
    prompts = {q.prompt[0].values[0] for q in started.questions}
    assert prompts == {"comer", "beber", "ver"}


def test_answer(
    session: Session,
    start: StartExerciseSession,
    answer: AnswerExerciseQuestion,
    user: UserORM,
    other_user: UserORM,
    n5: KanjiCollection,
) -> None:
    exercise = _exercise(session, user, n5, question_count=2)
    assert exercise.id is not None
    started = start.execute(user.id, exercise.id, "en")
    assert started.id is not None
    first, second = started.questions
    assert first.id is not None and second.id is not None

    with pytest.raises(EntityNotFoundError):
        answer.execute(other_user.id, started.id, first.id, OptionAnswer(option=0))
    with pytest.raises(InvalidAnswerError):
        answer.execute(user.id, started.id, first.id, OptionAnswer(option=4))

    after, graded = answer.execute(
        user.id, started.id, first.id, OptionAnswer(option=first.correct_option), 800
    )
    assert graded.is_correct is True
    assert graded.response_ms == 800
    assert after.finished_at is None
    with pytest.raises(QuestionAnsweredError):
        answer.execute(user.id, started.id, first.id, OptionAnswer(option=0))

    wrong = (second.correct_option + 1) % len(second.options)
    after, graded = answer.execute(
        user.id, started.id, second.id, OptionAnswer(option=wrong)
    )
    assert graded.is_correct is False
    assert after.finished_at is not None
    assert after.score == 1
