import pytest
from factories import make_entry_exercise, make_kanji_exercise
from sqlalchemy.orm import Session

from shodoukan_practice.application.queries import GetExercise, ListExercises
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import SqlAlchemyExerciseRepository


@pytest.fixture
def exercises(session: Session) -> SqlAlchemyExerciseRepository:
    return SqlAlchemyExerciseRepository(session)


def test_list_exercises(
    exercises: SqlAlchemyExerciseRepository, user: UserORM, other_user: UserORM
) -> None:
    exercises.add(make_entry_exercise(user.id, name="Verbs"))
    exercises.add(make_kanji_exercise(user.id, name="Kanji"))
    exercises.add(make_entry_exercise(other_user.id, name="Theirs"))

    listed = ListExercises(exercises).execute(user.id)

    assert [e.name for e in listed] == ["Kanji", "Verbs"]


def test_get_exercise(
    exercises: SqlAlchemyExerciseRepository, user: UserORM, other_user: UserORM
) -> None:
    exercise = exercises.add(make_entry_exercise(user.id))
    assert exercise.id is not None
    get = GetExercise(exercises)

    assert get.execute(user.id, exercise.id) == exercise
    with pytest.raises(EntityNotFoundError):
        get.execute(other_user.id, exercise.id)
