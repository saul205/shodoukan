"""The user's practice library: browsing it, importing entries and kanji, and
creating words of the user's own."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import StringConstraints

from ...application.commands import CreateOwnEntry, ImportEntry, ImportKanji
from ...application.queries import GetImportStatus, SearchEntries, SearchKanji
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_create_own_entry,
    get_import_entry,
    get_import_kanji,
    get_import_status,
    get_search_entries,
    get_search_kanji,
)
from ..schemas import (
    ImportedEntryResponse,
    ImportedKanjiResponse,
    ImportEntryRequest,
    ImportKanjiRequest,
    ImportStatusResponse,
    MeaningLang,
    NotInCollection,
    OwnEntryRequest,
    PracticeEntryPageResponse,
    PracticeEntryResponse,
    PracticeKanjiPageResponse,
    PracticeKanjiResponse,
    SearchText,
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


_LIST_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."}
}
_SEARCH_RESPONSES: dict[int | str, dict[str, str]] = {
    **_LIST_RESPONSES,
    status.HTTP_404_NOT_FOUND: {
        "description": "`not_in_collection` isn't one of the user's collections."
    },
}
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
Active = Annotated[
    bool | None,
    Query(
        description="Only active (`true`) or inactive (`false`) items; all if omitted."
    ),
]


@router.get(
    "/entries", response_model=PracticeEntryPageResponse, responses=_SEARCH_RESPONSES
)
def list_entries(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SearchEntries, Depends(get_search_entries)],
    q: SearchText = None,
    meaning_lang: MeaningLang = None,
    active: Active = None,
    not_in_collection: NotInCollection = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> PracticeEntryPageResponse:
    """The current user's imported entries, most recently imported first.

    With `q`, only the matching ones, best match first. Each `id` is what the
    collection endpoints take to add the entry.
    """
    page = use_case.execute(
        user.id,
        text=q,
        meaning_lang=meaning_lang,
        active=active,
        not_in_collection=not_in_collection,
        limit=limit,
        offset=offset,
    )
    session.commit()  # persists the user if this request created it
    return PracticeEntryPageResponse.model_validate(page)


@router.get(
    "/kanji", response_model=PracticeKanjiPageResponse, responses=_SEARCH_RESPONSES
)
def list_kanji(
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SearchKanji, Depends(get_search_kanji)],
    q: SearchText = None,
    meaning_lang: MeaningLang = None,
    active: Active = None,
    not_in_collection: NotInCollection = None,
    limit: Limit = 20,
    offset: Offset = 0,
) -> PracticeKanjiPageResponse:
    """The current user's imported kanji, most recently imported first.

    With `q`, only the matching ones, best match first.
    """
    page = use_case.execute(
        user.id,
        text=q,
        meaning_lang=meaning_lang,
        active=active,
        not_in_collection=not_in_collection,
        limit=limit,
        offset=offset,
    )
    session.commit()
    return PracticeKanjiPageResponse.model_validate(page)


_IMPORT_RESPONSES: dict[int | str, dict[str, str]] = {
    status.HTTP_200_OK: {"description": "Already in the library; returned as is."},
    status.HTTP_201_CREATED: {"description": "Imported into the library."},
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."},
    status.HTTP_404_NOT_FOUND: {
        "description": "Not in the dictionary, or no such collection for this user."
    },
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
    """Copy a dictionary entry into the current user's library.

    With `collection_ids`, it's also put in those entry collections, in the
    same transaction: an unknown collection fails with 404 and imports nothing.
    """
    result = use_case.execute(user.id, body.entry_id, body.collection_ids)
    session.commit()
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return PracticeEntryResponse.model_validate(result.item)


@router.post(
    "/entries/own",
    response_model=PracticeEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."},
        status.HTTP_404_NOT_FOUND: {
            "description": "A collection that isn't one of the user's."
        },
    },
)
def create_own_entry(
    body: OwnEntryRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[CreateOwnEntry, Depends(get_create_own_entry)],
) -> PracticeEntryResponse:
    """Create a word of the user's own, one the dictionary doesn't have.

    It has no `source_entry_id`; everything in it is the user's (`origin`
    `added`), so it can all be edited. `collection_ids` work as for imports.
    """
    entry = use_case.execute(
        user.id,
        body.spellings,
        body.readings,
        body.meaning,
        body.lang,
        body.collection_ids,
    )
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


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
    """Copy a dictionary kanji into the current user's library.

    `collection_ids` (kanji collections) work as for entries.
    """
    result = use_case.execute(user.id, body.literal, body.collection_ids)
    session.commit()
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return PracticeKanjiResponse.model_validate(result.item)
