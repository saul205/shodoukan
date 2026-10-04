"""Running an exercise: `POST /exercises/{id}/sessions` and
`/exercise-sessions/{id}`.

Another user's exercise or session is a 404, like a missing one.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from ...application.commands import AnswerExerciseQuestion, StartExerciseSession
from ...application.queries import GetExerciseSession
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_answer_exercise_question,
    get_get_exercise_session,
    get_start_exercise_session,
)
from ..schemas import (
    AnswerRequest,
    AnswerResponse,
    QuestionResponse,
    SessionResponse,
    StartSessionRequest,
)

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
}
_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "No such exercise, session or question."}
}

router = APIRouter(tags=["exercise sessions"], responses=_UNAUTHORIZED)


@router.post(
    "/exercises/{exercise_id}/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **_NOT_FOUND,
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid body, or the collections have too few usable "
            "items to ask about."
        },
    },
)
def start_exercise_session(
    exercise_id: int,
    body: StartSessionRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[StartExerciseSession, Depends(get_start_exercise_session)],
) -> SessionResponse:
    """Start a session: questions built from the active items of the
    exercise's collections. Solutions stay hidden until each is answered."""
    started = use_case.execute(user.id, exercise_id, body.meaning_lang)
    session.commit()
    return SessionResponse.of(started)


@router.get(
    "/exercise-sessions/{session_id}",
    response_model=SessionResponse,
    responses=_NOT_FOUND,
)
def get_exercise_session(
    session_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetExerciseSession, Depends(get_get_exercise_session)],
) -> SessionResponse:
    """A session, to go on playing or to review it."""
    found = use_case.execute(user.id, session_id)
    session.commit()
    return SessionResponse.of(found)


@router.post(
    "/exercise-sessions/{session_id}/questions/{question_id}/answer",
    response_model=AnswerResponse,
    responses={
        **_NOT_FOUND,
        status.HTTP_409_CONFLICT: {"description": "The question is answered already."},
    },
)
def answer_exercise_question(
    session_id: int,
    question_id: int,
    body: AnswerRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AnswerExerciseQuestion, Depends(get_answer_exercise_question)],
) -> AnswerResponse:
    """Answer a question once; returns it graded, with its solution."""
    updated, question = use_case.execute(
        user.id, session_id, question_id, body.answer, body.response_ms
    )
    session.commit()
    return AnswerResponse(
        question=QuestionResponse.of(question),
        finished_at=updated.finished_at,
        score=updated.score,
    )
