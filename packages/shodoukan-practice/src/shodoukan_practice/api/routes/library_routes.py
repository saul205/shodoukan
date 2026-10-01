"""The user's practice library: importing dictionary entries and kanji."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import StringConstraints

from ...application.commands import ImportEntry, ImportKanji
from ...application.queries import GetImportStatus
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_import_entry,
    get_import_kanji,
    get_import_status,
)
from ..schemas import (
    ImportedEntryResponse,
    ImportedKanjiResponse,
    ImportEntryRequest,
    ImportKanjiRequest,
    ImportStatusResponse,
    PracticeEntryResponse,
    PracticeKanjiResponse,
)

router = APIRouter(prefix="/library", tags=["library"])

# A search results page holds at most 100 items (shodoukan-api's `limit`).
MAX_LOOKUP = 100

KanjiLiteral = Annotated[str, StringConstraints(min_length=1, max_length=1)]


@router.get(
    "/imported",
    response_model=ImportStatusResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
    },
)
def get_imported(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetImportStatus, Depends(get_import_status)],
    entry_ids: Annotated[
        list[int],
        Query(
            max_length=MAX_LOOKUP,
            description="Dictionary entry ids (repeat the parameter).",
        ),
    ] = [],  # noqa: B006 - FastAPI copies query defaults per request
    literals: Annotated[
        list[KanjiLiteral],
        Query(
            max_length=MAX_LOOKUP,
            description="Kanji characters (repeat the parameter).",
        ),
    ] = [],  # noqa: B006
) -> ImportStatusResponse:
    """Which of these dictionary items the current user has imported.

    Meant for the dictionary page: search with shodoukan-api's `/search`,
    then ask this with the result ids to enable or disable each Import
    button. Only imported items are returned, with their practice ids.
    """
    result = use_case.execute(user.id, entry_ids, literals)
    session.commit()  # persists the user if this request created it
    return ImportStatusResponse(
        entries=[
            ImportedEntryResponse(source_entry_id=source_id, id=practice_id)
            for source_id, practice_id in result.entries.items()
        ],
        kanji=[
            ImportedKanjiResponse(literal=literal, id=practice_id)
            for literal, practice_id in result.kanji.items()
        ],
    )


_IMPORT_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_200_OK: {"description": "Already in the library; returned as is."},
    status.HTTP_201_CREATED: {"description": "Imported into the library."},
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."},
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
    result = use_case.execute(user.id, body.entry_id)
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
    result = use_case.execute(user.id, body.literal)
    session.commit()
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return PracticeKanjiResponse.model_validate(result.item)
