"""One kanji of the user's library: its detail and its customisation.

Same rules as `practice_entry_routes`: every edit returns the whole kanji,
and dictionary meanings can only be disabled (409 otherwise).
"""

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from ...application.commands import (
    AddKanjiMeaning,
    EditKanjiMeaning,
    RemoveKanjiFromLibrary,
    RemoveKanjiMeaning,
    SetKanjiActive,
    SetKanjiNotes,
    SetKanjiPartEnabled,
)
from ...application.queries import GetLibraryKanji, ListCollectionsOfKanji
from ...domain.entities import KanjiPart
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_add_kanji_meaning,
    get_edit_kanji_meaning,
    get_get_library_kanji,
    get_list_collections_of_kanji,
    get_remove_kanji_from_library,
    get_remove_kanji_meaning,
    get_set_kanji_active,
    get_set_kanji_notes,
    get_set_kanji_part_enabled,
)
from ..schemas import (
    ActiveRequest,
    CollectionResponse,
    EnabledRequest,
    MeaningTextRequest,
    NewKanjiMeaningRequest,
    NotesRequest,
    PracticeKanjiResponse,
)

_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."},
    status.HTTP_404_NOT_FOUND: {
        "description": "Not in the user's library, or no such nested item."
    },
}
_ORIGINAL: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "description": "A dictionary meaning: it can only be disabled."
    }
}

router = APIRouter(prefix="/library/kanji", tags=["library"], responses=_RESPONSES)


class KanjiPartPath(StrEnum):
    """The parts that can be enabled or disabled, as they appear in the URL.

    `readings` covers on, kun and nanori.
    """

    READINGS = "readings"
    MEANINGS = "meanings"


_PARTS: dict[KanjiPartPath, KanjiPart] = {
    KanjiPartPath.READINGS: "readings",
    KanjiPartPath.MEANINGS: "meanings",
}


@router.get("/{kanji_id}", response_model=PracticeKanjiResponse)
def get_kanji(
    kanji_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetLibraryKanji, Depends(get_get_library_kanji)],
) -> PracticeKanjiResponse:
    """The user's copy of a kanji, with its practice state and notes."""
    kanji = use_case.execute(user.id, kanji_id)
    session.commit()  # persists the user if this request created it
    return PracticeKanjiResponse.model_validate(kanji)


@router.delete("/{kanji_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_kanji(
    kanji_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveKanjiFromLibrary, Depends(get_remove_kanji_from_library)],
) -> None:
    """Remove the kanji from the library and from every collection."""
    use_case.execute(user.id, kanji_id)
    session.commit()


@router.get("/{kanji_id}/collections", response_model=list[CollectionResponse])
def list_kanji_collections(
    kanji_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ListCollectionsOfKanji, Depends(get_list_collections_of_kanji)],
) -> list[CollectionResponse]:
    """The collections (tags) the kanji is in, by name."""
    collections = use_case.execute(user.id, kanji_id)
    session.commit()
    return [CollectionResponse.model_validate(c) for c in collections]


@router.put("/{kanji_id}/active", response_model=PracticeKanjiResponse)
def set_active(
    kanji_id: int,
    body: ActiveRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetKanjiActive, Depends(get_set_kanji_active)],
) -> PracticeKanjiResponse:
    """Activate or deactivate the kanji (inactive ones aren't practised)."""
    kanji = use_case.execute(user.id, kanji_id, body.active)
    session.commit()
    return PracticeKanjiResponse.model_validate(kanji)


@router.put("/{kanji_id}/notes", response_model=PracticeKanjiResponse)
def set_notes(
    kanji_id: int,
    body: NotesRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetKanjiNotes, Depends(get_set_kanji_notes)],
) -> PracticeKanjiResponse:
    """Replace the kanji's note."""
    kanji = use_case.execute(user.id, kanji_id, body.notes)
    session.commit()
    return PracticeKanjiResponse.model_validate(kanji)


@router.put(
    "/{kanji_id}/{part}/{item_id}/enabled", response_model=PracticeKanjiResponse
)
def set_enabled(
    kanji_id: int,
    part: KanjiPartPath,
    item_id: int,
    body: EnabledRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetKanjiPartEnabled, Depends(get_set_kanji_part_enabled)],
) -> PracticeKanjiResponse:
    """Show or hide one reading or meaning by its `id`."""
    kanji = use_case.execute(user.id, kanji_id, _PARTS[part], item_id, body.enabled)
    session.commit()
    return PracticeKanjiResponse.model_validate(kanji)


@router.post(
    "/{kanji_id}/meanings",
    response_model=PracticeKanjiResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_meaning(
    kanji_id: int,
    body: NewKanjiMeaningRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddKanjiMeaning, Depends(get_add_kanji_meaning)],
) -> PracticeKanjiResponse:
    """Add a meaning of the user's own at the end."""
    kanji = use_case.execute(user.id, kanji_id, body.text, body.lang)
    session.commit()
    return PracticeKanjiResponse.model_validate(kanji)


@router.put(
    "/{kanji_id}/meanings/{meaning_id}",
    response_model=PracticeKanjiResponse,
    responses=_ORIGINAL,
)
def edit_meaning(
    kanji_id: int,
    meaning_id: int,
    body: MeaningTextRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[EditKanjiMeaning, Depends(get_edit_kanji_meaning)],
) -> PracticeKanjiResponse:
    """Change the text of one of the user's own meanings."""
    kanji = use_case.execute(user.id, kanji_id, meaning_id, body.text)
    session.commit()
    return PracticeKanjiResponse.model_validate(kanji)


@router.delete(
    "/{kanji_id}/meanings/{meaning_id}",
    response_model=PracticeKanjiResponse,
    responses=_ORIGINAL,
)
def remove_meaning(
    kanji_id: int,
    meaning_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveKanjiMeaning, Depends(get_remove_kanji_meaning)],
) -> PracticeKanjiResponse:
    """Remove one of the user's own meanings."""
    kanji = use_case.execute(user.id, kanji_id, meaning_id)
    session.commit()
    return PracticeKanjiResponse.model_validate(kanji)
