"""Statistics over the user's sessions: `GET /exercises/{id}/statistics` for
one exercise and `GET /statistics` overall. Read-only; computed when asked.
"""

from typing import Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...application.queries import (
    MAX_ACTIVITY_DAYS,
    GetExerciseStatistics,
    GetPracticeStatistics,
)
from ...domain.clock import utc_now
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_get_exercise_statistics,
    get_get_practice_statistics,
)
from ..schemas import ExerciseStatisticsResponse, PracticeStatisticsResponse

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
}

router = APIRouter(tags=["statistics"], responses=_UNAUTHORIZED)


@router.get(
    "/exercises/{exercise_id}/statistics",
    response_model=ExerciseStatisticsResponse,
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such exercise."}},
)
def get_exercise_statistics(
    exercise_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetExerciseStatistics, Depends(get_get_exercise_statistics)],
) -> ExerciseStatisticsResponse:
    """How the user does in an exercise: totals, accuracy per direction and
    the items missed most."""
    statistics = use_case.execute(user.id, exercise_id)
    session.commit()
    return ExerciseStatisticsResponse.of(statistics)


@router.get(
    "/statistics",
    response_model=PracticeStatisticsResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Unknown time zone, or `days` out of range."
        }
    },
)
def get_practice_statistics(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetPracticeStatistics, Depends(get_get_practice_statistics)],
    days: Annotated[int, Query(ge=1, le=MAX_ACTIVITY_DAYS)] = 30,
    tz: Annotated[
        str, Query(description="IANA time zone the days are counted in.")
    ] = "UTC",
) -> PracticeStatisticsResponse:
    """How the user does overall: totals, answers per day over the last
    `days` days (today included), each exercise's figures, and the words and
    kanji missed most."""
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"unknown time zone: {tz}"
        ) from None
    statistics = use_case.execute(user.id, utc_now(), days, zone)
    session.commit()
    return PracticeStatisticsResponse.of(statistics)
