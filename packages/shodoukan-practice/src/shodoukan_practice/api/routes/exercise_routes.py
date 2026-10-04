"""The user's saved exercises: `/exercises`.

Another user's exercise or collection is a 404, like a missing one. Settings
that don't fit the exercise's item kind are a 422.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from ...application.commands import CreateExercise, DeleteExercise, UpdateExercise
from ...application.queries import GetExercise, ListExercises
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_create_exercise,
    get_delete_exercise,
    get_get_exercise,
    get_list_exercises,
    get_update_exercise,
)
from ..schemas import ExerciseRequest, ExerciseResponse, NewExerciseRequest

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {
        "description": "No such exercise or collection for this user."
    }
}

router = APIRouter(prefix="/exercises", tags=["exercises"], responses=_UNAUTHORIZED)


@router.get("", response_model=list[ExerciseResponse])
def list_exercises(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ListExercises, Depends(get_list_exercises)],
) -> list[ExerciseResponse]:
    """The current user's exercises, by name."""
    exercises = use_case.execute(user.id)
    session.commit()  # persists the user if this request created it
    return [ExerciseResponse.model_validate(e) for e in exercises]


@router.post(
    "",
    response_model=ExerciseResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_NOT_FOUND,
)
def create_exercise(
    body: NewExerciseRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[CreateExercise, Depends(get_create_exercise)],
) -> ExerciseResponse:
    """Save an exercise over some of the user's collections of its kind."""
    exercise = use_case.execute(
        user.id,
        body.item_kind,
        body.name,
        body.description,
        body.collection_ids,
        body.settings,
    )
    session.commit()
    return ExerciseResponse.model_validate(exercise)


@router.get("/{exercise_id}", response_model=ExerciseResponse, responses=_NOT_FOUND)
def get_exercise(
    exercise_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetExercise, Depends(get_get_exercise)],
) -> ExerciseResponse:
    """One of the current user's exercises."""
    exercise = use_case.execute(user.id, exercise_id)
    session.commit()
    return ExerciseResponse.model_validate(exercise)


@router.put("/{exercise_id}", response_model=ExerciseResponse, responses=_NOT_FOUND)
def update_exercise(
    exercise_id: int,
    body: ExerciseRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[UpdateExercise, Depends(get_update_exercise)],
) -> ExerciseResponse:
    """Replace the exercise's fields (send all of them); its kind stays."""
    exercise = use_case.execute(
        user.id,
        exercise_id,
        body.name,
        body.description,
        body.collection_ids,
        body.settings,
    )
    session.commit()
    return ExerciseResponse.model_validate(exercise)


@router.delete(
    "/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_NOT_FOUND
)
def delete_exercise(
    exercise_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[DeleteExercise, Depends(get_delete_exercise)],
) -> None:
    """Delete the exercise. Its collections stay."""
    use_case.execute(user.id, exercise_id)
    session.commit()
