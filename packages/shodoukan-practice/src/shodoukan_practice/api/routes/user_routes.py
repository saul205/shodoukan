"""The signed-in user."""

from fastapi import APIRouter, status

from ..deps import CurrentUserDep, SessionDep
from ..schemas import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
    },
)
def get_me(user: CurrentUserDep, session: SessionDep) -> UserResponse:
    """The current user's practice profile, created on their first request."""
    session.commit()  # persists the user if this request created it
    return UserResponse.model_validate(user)
