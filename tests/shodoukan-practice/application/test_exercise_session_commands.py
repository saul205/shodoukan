from datetime import timedelta
from random import Random
from typing import Any

import pytest
from factories import (
    choice_settings,
    make_kanji_collection,
    make_kanji_with,
    make_session,
    make_word,
)
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import (
    AnswerExerciseQuestion,
    CreateExercise,
    FinishExerciseSession,
    StartExerciseSession,
)
from shodoukan_practice.application.queries import GetExerciseSession
from shodoukan_practice.domain.clock import utc_now
from shodoukan_practice.domain.entities import (
    EntryCollection,
    Exercise,
    ExerciseSession,
    KanjiCollection,
    OptionAnswer,
)
from shodoukan_practice.domain.entities.exercise_session_entity import IDLE_TIMEOUT
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    ExercisePoolTooSmallError,
    InvalidAnswerError,
    QuestionNotActiveError,
    SessionFinishedError,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
    SqlAlchemyUserRepository,
)

KANJI = [
    ("食", "ショク", "た.べる", "eat"),
    ("水", "スイ", "みず", "water"),
    ("火", "カ", "ひ", "fire"),
    ("木", "モク", "き", "tree"),
    ("山", "サン", "やま", "mountain"),
]


Repos = tuple[
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
]


def _start_use_case(session: Session, rng: Random) -> StartExerciseSession:
    return StartExerciseSession(
        *_repos(session), SqlAlchemyUserRepository(session), rng=rng
    )


def _repos(session: Session) -> Repos:
    return (
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyExerciseSessionRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


@pytest.fixture
def start(session: Session) -> StartExerciseSession:
    return _start_use_case(session, Random(7))


@pytest.fixture
def answer(session: Session) -> AnswerExerciseQuestion:
    return AnswerExerciseQuestion(*_repos(session), Random(7))


@pytest.fixture
def sessions(session: Session) -> SqlAlchemyExerciseSessionRepository:
    return SqlAlchemyExerciseSessionRepository(session)


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


@pytest.fixture
def exercise(session: Session, user: UserORM, n5: KanjiCollection) -> Exercise:
    assert n5.id is not None
    return CreateExercise(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    ).execute(
        user.id,
        "kanji",
        "N5",
        None,
        [n5.id],
        choice_settings((("literal",), "kunyomi"), back_fields=["meaning"]),
    )


def _start(
    start: StartExerciseSession, user: UserORM, exercise: Exercise
) -> ExerciseSession:
    assert exercise.id is not None
    return start.execute(user.id, exercise.id, "en")


def _reply(
    answer: AnswerExerciseQuestion,
    user: UserORM,
    session: ExerciseSession,
    right: bool = True,
) -> Any:
    """Answer the session's active question, right or wrong."""
    assert session.id is not None and session.current is not None
    current = session.current
    assert current.id is not None
    option = current.correct_option
    if not right:
        option = (option + 1) % len(current.options)
    return answer.execute(user.id, session.id, current.id, OptionAnswer(option=option))


def test_start_asks_the_first_question(
    session: Session,
    start: StartExerciseSession,
    user: UserORM,
    exercise: Exercise,
) -> None:
    started = _start(start, user, exercise)

    assert started.id is not None
    assert started.exercise_id == exercise.id
    assert started.exercise_name == "N5"
    assert started.item_kind == "kanji"
    assert started.history == []
    assert started.current is not None
    assert started.current.id is not None
    assert len(started.current.options) == 4
    assert started.finished_at is None
    got = GetExerciseSession(SqlAlchemyExerciseSessionRepository(session))
    assert got.execute(user.id, started.id) == started


def test_answering_asks_the_next_question_from_the_deck(
    start: StartExerciseSession,
    answer: AnswerExerciseQuestion,
    user: UserORM,
    exercise: Exercise,
) -> None:
    current = _start(start, user, exercise)
    asked = []
    for _ in range(10):
        assert current.current is not None
        asked.append(current.current.item_id)
        current, graded, nxt = _reply(answer, user, current)
        assert graded.is_correct is True
        assert nxt == current.current
    assert len(set(asked[:5])) == 5  # a full round before any repeat
    assert len(set(asked[5:])) == 5
    assert (current.answered, current.score) == (10, 10)
    assert current.finished_at is None


def test_answer_errors(
    start: StartExerciseSession,
    answer: AnswerExerciseQuestion,
    user: UserORM,
    other_user: UserORM,
    exercise: Exercise,
) -> None:
    started = _start(start, user, exercise)
    assert started.id is not None and started.current is not None
    question_id = started.current.id
    assert question_id is not None

    with pytest.raises(EntityNotFoundError):
        answer.execute(other_user.id, started.id, question_id, OptionAnswer(option=0))
    with pytest.raises(InvalidAnswerError):
        answer.execute(user.id, started.id, question_id, OptionAnswer(option=4))
    answer.execute(user.id, started.id, question_id, OptionAnswer(option=0))
    with pytest.raises(QuestionNotActiveError):  # a double click
        answer.execute(user.id, started.id, question_id, OptionAnswer(option=0))


def test_start_closes_the_users_open_session_of_any_exercise(
    session: Session,
    start: StartExerciseSession,
    sessions: SqlAlchemyExerciseSessionRepository,
    user: UserORM,
    other_user: UserORM,
    exercise: Exercise,
    n5: KanjiCollection,
) -> None:
    assert n5.id is not None
    other_exercise = CreateExercise(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    ).execute(
        user.id,
        "kanji",
        "N5 on'yomi",
        None,
        [n5.id],
        choice_settings((("literal",), "onyomi")),
    )
    theirs = sessions.add(make_session(other_user.id, question_id=None))
    first = _start(start, user, exercise)
    assert first.id is not None and theirs.id is not None

    second = _start(start, user, other_exercise)  # a different exercise

    closed = sessions.get(first.id, user.id)
    assert closed is not None
    # Closed at its last activity, which stays what it was.
    assert closed.finished_at == first.updated_at
    assert closed.updated_at == first.updated_at
    assert closed.current is None
    assert [s.id for s in sessions.list_open(user.id)] == [second.id]
    untouched = sessions.get(theirs.id, other_user.id)
    assert untouched is not None
    assert untouched.finished_at is None  # other users keep theirs


def test_finish(
    start: StartExerciseSession,
    answer: AnswerExerciseQuestion,
    sessions: SqlAlchemyExerciseSessionRepository,
    user: UserORM,
    exercise: Exercise,
) -> None:
    started = _start(start, user, exercise)
    started, _, _ = _reply(answer, user, started)
    assert started.id is not None
    finish = FinishExerciseSession(sessions)

    finished = finish.execute(user.id, started.id)

    assert finished.finished_at is not None
    assert finished.current is None
    assert finished.answered == 1
    assert finish.execute(user.id, started.id) == finished  # idempotent
    with pytest.raises(SessionFinishedError):
        answer.execute(user.id, started.id, 1, OptionAnswer(option=0))


def _make_idle(
    sessions: SqlAlchemyExerciseSessionRepository, started: ExerciseSession
) -> ExerciseSession:
    """Store the session as if its last activity was long ago."""
    started.updated_at = utc_now() - IDLE_TIMEOUT - timedelta(minutes=1)
    return sessions.update(started)


def test_an_idle_session_refuses_answers_without_writing(
    start: StartExerciseSession,
    answer: AnswerExerciseQuestion,
    sessions: SqlAlchemyExerciseSessionRepository,
    user: UserORM,
    exercise: Exercise,
) -> None:
    idle = _make_idle(sessions, _start(start, user, exercise))
    assert idle.id is not None

    with pytest.raises(SessionFinishedError):
        _reply(answer, user, idle)

    stored = sessions.get(idle.id, user.id)
    assert stored == idle  # nothing written
    assert stored.finished_at is None
    assert stored.ended_at(utc_now()) == idle.updated_at  # but it has ended


def test_an_idle_session_is_closed_for_good_by_the_next_start(
    start: StartExerciseSession,
    sessions: SqlAlchemyExerciseSessionRepository,
    user: UserORM,
    exercise: Exercise,
) -> None:
    idle = _make_idle(sessions, _start(start, user, exercise))
    assert idle.id is not None

    _start(start, user, exercise)

    closed = sessions.get(idle.id, user.id)
    assert closed is not None
    assert closed.finished_at == idle.updated_at
    assert closed.current is None


def test_finishing_an_idle_session_closes_it_at_its_last_activity(
    start: StartExerciseSession,
    sessions: SqlAlchemyExerciseSessionRepository,
    user: UserORM,
    exercise: Exercise,
) -> None:
    idle = _make_idle(sessions, _start(start, user, exercise))
    assert idle.id is not None

    finished = FinishExerciseSession(sessions).execute(user.id, idle.id)

    assert finished.finished_at == idle.updated_at
    assert finished.updated_at == idle.updated_at


def test_deleted_exercise_keeps_the_answer_and_finishes(
    session: Session,
    start: StartExerciseSession,
    answer: AnswerExerciseQuestion,
    user: UserORM,
    exercise: Exercise,
) -> None:
    started = _start(start, user, exercise)
    SqlAlchemyExerciseRepository(session).delete(exercise)
    session.expire_all()
    assert started.id is not None
    reloaded = SqlAlchemyExerciseSessionRepository(session).get(started.id, user.id)
    assert reloaded is not None

    after, graded, nxt = _reply(answer, user, reloaded)

    assert graded.is_correct is True
    assert nxt is None
    assert after.finished_at is not None
    assert after.answered == 1


def test_pool_too_small(
    session: Session,
    start: StartExerciseSession,
    user: UserORM,
    exercise: Exercise,
    n5: KanjiCollection,
) -> None:
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    for item in kanji.get_many(range(1, 100), user.id):
        if item.literal != "食":
            item.deactivate()
            kanji.update(item)
    with pytest.raises(ExercisePoolTooSmallError):
        _start(start, user, exercise)

    SqlAlchemyKanjiCollectionRepository(session).delete(n5)
    session.expire_all()
    with pytest.raises(ExercisePoolTooSmallError):  # no collections left
        _start(start, user, exercise)


def test_no_next_question_when_the_pool_shrinks(
    session: Session,
    start: StartExerciseSession,
    answer: AnswerExerciseQuestion,
    user: UserORM,
    exercise: Exercise,
) -> None:
    started = _start(start, user, exercise)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    for item in kanji.get_many(range(1, 100), user.id):
        item.deactivate()
        kanji.update(item)

    after, _, nxt = _reply(answer, user, started)

    assert nxt is None
    assert after.finished_at is None  # still open: the user can finish it


def test_unknown_or_foreign_exercise(
    start: StartExerciseSession,
    user: UserORM,
    other_user: UserORM,
    exercise: Exercise,
) -> None:
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
    verbs = collections.add(EntryCollection(id=None, user_id=user.id, name="verbs"))
    words = [
        ("食べる", "たべる", "comer"),
        ("飲む", "のむ", "beber"),
        ("見る", "みる", "ver"),
    ]
    for i, (writing, reading, meaning) in enumerate(words):
        entry = make_word(user.id, i + 1, writing, reading, [(meaning, "spa")])
        collections.add_item(verbs, entries.add(entry))
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
    assert started.current is not None
    assert started.current.prompt[0].values[0] in {"comer", "beber", "ver"}
