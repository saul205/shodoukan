"""Running an exercise: `POST /exercises/{id}/sessions` and
`/exercise-sessions/{id}`.

A session has one active question; answering it returns the next one. It lasts
until it's finished, or until it's idle for 30 minutes. Another user's
exercise or session is a 404, like a missing one.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from ...application.commands import (
    AnswerExerciseQuestion,
    FinishExerciseSession,
    StartExerciseSession,
)
from ...application.queries import GetExerciseSession
from ...domain.clock import utc_now
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_answer_exercise_question,
    get_finish_exercise_session,
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
    status.HTTP_404_NOT_FOUND: {"description": "No such exercise or session."}
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
    """Start studying: a new session with its first active question.

    The user's open sessions of this exercise are finished."""
    started = use_case.execute(user.id, exercise_id, body.meaning_lang)
    session.commit()
    return SessionResponse.of(started, utc_now())


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
    """A session, to go on studying (its active question) or to review it."""
    found = use_case.execute(user.id, session_id)
    session.commit()
    return SessionResponse.of(found, utc_now())


@router.post(
    "/exercise-sessions/{session_id}/answer",
    response_model=AnswerResponse,
    responses={
        **_NOT_FOUND,
        status.HTTP_409_CONFLICT: {
            "description": "The session is finished (or was idle too long), or "
            "`question_id` isn't the active question."
        },
    },
)
def answer_exercise_question(
    session_id: int,
    body: AnswerRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AnswerExerciseQuestion, Depends(get_answer_exercise_question)],
) -> AnswerResponse:
    """Answer the active question; returns it graded and the next one."""
    updated, answered, next_question = use_case.execute(
        user.id, session_id, body.question_id, body.answer, body.response_ms
    )
    session.commit()
    return AnswerResponse(
        answered=QuestionResponse.of(answered),
        next=QuestionResponse.of(next_question) if next_question else None,
        answered_count=updated.answered,
        score=updated.score,
        finished_at=updated.finished_at,
    )


@router.post(
    "/exercise-sessions/{session_id}/finish",
    response_model=SessionResponse,
    responses=_NOT_FOUND,
)
def finish_exercise_session(
    session_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[FinishExerciseSession, Depends(get_finish_exercise_session)],
) -> SessionResponse:
    """Stop studying. The active question, never answered, is dropped.

    Finishing a finished session changes nothing."""
    finished = use_case.execute(user.id, session_id)
    session.commit()
    return SessionResponse.of(finished, utc_now())
