"""The user's practice library: importing dictionary entries and kanji."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from ...application.commands import ImportEntry, ImportKanji
from ..deps import CurrentUserDep, SessionDep, get_import_entry, get_import_kanji
from ..schemas import (
    ImportEntryRequest,
    ImportKanjiRequest,
    PracticeEntryResponse,
    PracticeKanjiResponse,
)

router = APIRouter(prefix="/library", tags=["library"])

_IMPORT_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_200_OK: {"description": "Already in the library; returned as is."},
    status.HTTP_201_CREATED: {"description": "Imported into the library."},
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."},
    status.HTTP_403_FORBIDDEN: {"description": "User not registered."},
    status.HTTP_404_NOT_FOUND: {"description": "Not in the dictionary."},
}


@router.post(
    "/entries",
    response_model=PracticeEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_IMPORT_RESPONSES,
)
def import_entry(
    body: ImportEntryRequest,
    response: Response,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ImportEntry, Depends(get_import_entry)],
) -> PracticeEntryResponse:
    """Copy a dictionary entry into the current user's library."""
    result = use_case.execute(_user_id(user.id), body.entry_id)
    session.commit()
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return PracticeEntryResponse.model_validate(result.item)


@router.post(
    "/kanji",
    response_model=PracticeKanjiResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_IMPORT_RESPONSES,
)
def import_kanji(
    body: ImportKanjiRequest,
    response: Response,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ImportKanji, Depends(get_import_kanji)],
) -> PracticeKanjiResponse:
    """Copy a dictionary kanji into the current user's library."""
    result = use_case.execute(_user_id(user.id), body.literal)
    session.commit()
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return PracticeKanjiResponse.model_validate(result.item)


def _user_id(user_id: int | None) -> int:
    # Users from the repository are always stored, so they have an id.
    if user_id is None:
        raise RuntimeError("stored user without id")
    return user_id
