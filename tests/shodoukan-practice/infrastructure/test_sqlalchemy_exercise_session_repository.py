import pytest
from factories import make_kanji, make_kanji_exercise, make_question, make_session
from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import OptionAnswer
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    QuestionNotActiveError,
)
from shodoukan_practice.infrastructure.db.orm import ExerciseQuestionORM, UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyExerciseSessionRepository:
    return SqlAlchemyExerciseSessionRepository(session)


def test_add_gives_ids_and_get_reads_it_back(
    repo: SqlAlchemyExerciseSessionRepository, user: UserORM, other_user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, question_id=None))

    assert stored.id is not None
    assert stored.current is not None
    assert stored.current.id is not None
    assert stored.history == []
    assert repo.get(stored.id, user.id) == stored
    assert repo.get(stored.id, other_user.id) is None


def test_answer_and_ask_round_trip(
    session: Session, repo: SqlAlchemyExerciseSessionRepository, user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, question_id=None))
    assert stored.id is not None and stored.current is not None
    first = stored.current.id
    assert first is not None
    stored.answer(first, OptionAnswer(option=0), response_ms=500)
    stored.ask(make_question(0))

    updated = repo.update(stored)
    session.expire_all()

    loaded = repo.get(stored.id, user.id)
    assert loaded == updated
    assert loaded is not None
    assert [q.id for q in loaded.history] == [first]  # kept its id
    assert loaded.current is not None
    assert loaded.current.id not in (None, first)
    assert loaded.current.position == 1
    # The active question's answer is SQL NULL, so statistics can filter on it.
    unanswered = session.scalars(
        select(ExerciseQuestionORM.id).where(ExerciseQuestionORM.answer.is_(None))
    ).all()
    assert unanswered == [loaded.current.id]


def test_finish_deletes_the_active_question(
    session: Session, repo: SqlAlchemyExerciseSessionRepository, user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, question_id=None))
    assert stored.id is not None
    stored.finish()
    repo.update(stored)
    session.expire_all()

    loaded = repo.get(stored.id, user.id)
    assert loaded is not None
    assert loaded.current is None
    assert loaded.finished_at is not None
    assert session.scalars(select(ExerciseQuestionORM.id)).all() == []


def test_list_open(
    repo: SqlAlchemyExerciseSessionRepository,
    session: Session,
    user: UserORM,
    other_user: UserORM,
) -> None:
    exercises = SqlAlchemyExerciseRepository(session)
    mine = exercises.add(make_kanji_exercise(user.id))
    other = exercises.add(make_kanji_exercise(user.id, name="Other"))
    assert mine.id is not None
    open_one = repo.add(make_session(user.id, mine.id, question_id=None))
    closed = repo.add(make_session(user.id, mine.id, question_id=None))
    closed.finish()
    repo.update(closed)
    repo.add(make_session(user.id, other.id, question_id=None))

    assert [s.id for s in repo.list_open(user.id, mine.id)] == [open_one.id]
    assert repo.list_open(other_user.id, mine.id) == []


def test_update_of_a_foreign_session(
    repo: SqlAlchemyExerciseSessionRepository, user: UserORM, other_user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, question_id=None))
    with pytest.raises(EntityNotFoundError):
        repo.update(stored.model_copy(update={"user_id": other_user.id}))
    with pytest.raises(EntityNotFoundError):
        repo.update(make_session(user.id))  # never stored


def test_history_survives_removing_the_exercise_and_items(
    session: Session, repo: SqlAlchemyExerciseSessionRepository, user: UserORM
) -> None:
    exercises = SqlAlchemyExerciseRepository(session)
    kanji_repo = SqlAlchemyPracticeKanjiRepository(session)
    exercise = exercises.add(make_kanji_exercise(user.id))
    kanji = kanji_repo.add(make_kanji(user.id))
    stored = repo.add(make_session(user.id, exercise.id, kanji.id, question_id=None))
    assert stored.id is not None and stored.current is not None
    assert stored.current.id is not None
    stored.answer(stored.current.id, OptionAnswer(option=0))
    repo.update(stored)

    exercises.delete(exercise)
    kanji_repo.delete(kanji)
    session.expire_all()

    kept = repo.get(stored.id, user.id)
    assert kept is not None
    assert kept.exercise_id is None
    assert kept.exercise_name == "N5 kanji"
    assert kept.history[0].item_id is None
    assert kept.history[0].prompt == stored.history[0].prompt


def test_get_for_update_reads_like_get(
    repo: SqlAlchemyExerciseSessionRepository, user: UserORM, other_user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, question_id=None))
    assert stored.id is not None
    assert repo.get_for_update(stored.id, user.id) == repo.get(stored.id, user.id)
    assert repo.get_for_update(stored.id, other_user.id) is None


def test_a_racing_answer_is_refused(
    session: Session, repo: SqlAlchemyExerciseSessionRepository, user: UserORM
) -> None:
    # Two requests read the session before either stores its answer (what the
    # row lock prevents on PostgreSQL): the second can't store its next
    # question at the same position.
    stored = repo.add(make_session(user.id, question_id=None))
    assert stored.id is not None and stored.current is not None
    question_id = stored.current.id
    assert question_id is not None
    first, second = stored.model_copy(deep=True), stored.model_copy(deep=True)
    for copy, option in ((first, 0), (second, 1)):
        copy.answer(question_id, OptionAnswer(option=option))
        copy.ask(make_question(0))

    repo.update(first)
    with pytest.raises(QuestionNotActiveError):
        repo.update(second)
    session.expire_all()

    kept = repo.get(stored.id, user.id)
    assert kept is not None
    assert kept.history[0].answer == OptionAnswer(option=0)  # the first one
    assert kept.current is not None
    assert kept.current.position == 1


def test_question_positions_are_unique_per_session(
    session: Session, repo: SqlAlchemyExerciseSessionRepository, user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, question_id=None))
    row = session.scalars(select(ExerciseQuestionORM)).one()
    columns = {
        c.name: getattr(row, c.name)
        for c in ExerciseQuestionORM.__table__.columns
        if c.name != "id"
    }
    assert stored.id is not None
    with pytest.raises(IntegrityError), session.begin_nested():
        session.execute(insert(ExerciseQuestionORM).values(**columns))
