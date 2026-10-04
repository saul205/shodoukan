import pytest
from factories import make_kanji, make_kanji_exercise, make_session
from sqlalchemy import select
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import OptionAnswer
from shodoukan_practice.domain.exceptions import EntityNotFoundError
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
    stored = repo.add(make_session(user.id, questions=3, stored=False))

    assert stored.id is not None
    assert all(q.id is not None for q in stored.questions)
    assert [q.position for q in stored.questions] == [0, 1, 2]
    assert repo.get(stored.id, user.id) == stored
    assert repo.get(stored.id, other_user.id) is None


def test_update_stores_answers(
    session: Session, repo: SqlAlchemyExerciseSessionRepository, user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, questions=2, stored=False))
    first = stored.questions[0].id
    assert first is not None and stored.id is not None
    stored.answer(first, OptionAnswer(option=0), response_ms=500)

    repo.update(stored)
    session.expire_all()

    loaded = repo.get(stored.id, user.id)
    assert loaded == stored
    assert loaded is not None
    assert loaded.questions[0].is_correct is True
    # Unanswered answers are SQL NULL, so statistics can filter on them.
    unanswered = session.scalars(
        select(ExerciseQuestionORM.id).where(ExerciseQuestionORM.answer.is_(None))
    ).all()
    assert unanswered == [stored.questions[1].id]


def test_update_of_a_foreign_session(
    repo: SqlAlchemyExerciseSessionRepository, user: UserORM, other_user: UserORM
) -> None:
    stored = repo.add(make_session(user.id, stored=False))
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
    stored = repo.add(
        make_session(user.id, exercise.id, item_ids=(kanji.id,), stored=False)
    )

    exercises.delete(exercise)
    kanji_repo.delete(kanji)
    session.expire_all()

    assert stored.id is not None
    kept = repo.get(stored.id, user.id)
    assert kept is not None
    assert kept.exercise_id is None
    assert kept.exercise_name == "N5 kanji"
    assert kept.questions[0].item_id is None
    assert kept.questions[0].prompt == stored.questions[0].prompt
