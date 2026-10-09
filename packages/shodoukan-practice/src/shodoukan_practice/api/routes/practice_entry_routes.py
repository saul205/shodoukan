"""One entry of the user's library: its detail and its customisation.

Every edit returns the whole entry as it is now, so the client re-renders
from the response. Dictionary data is only ever disabled: editing or
removing an imported spelling, reading, sense, meaning or example is a 409.
"""

from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from ...application.commands import (
    AddEntryExample,
    AddEntryGloss,
    AddEntryReading,
    AddEntrySense,
    AddEntrySpelling,
    EditEntryExample,
    EditEntryGloss,
    RemoveEntryExample,
    RemoveEntryFromLibrary,
    RemoveEntryGloss,
    RemoveEntryReading,
    RemoveEntrySense,
    RemoveEntrySpelling,
    SetEntryActive,
    SetEntryNotes,
    SetEntryPartEnabled,
    SetSenseNotes,
)
from ...application.queries import GetLibraryEntry, ListCollectionsOfEntry
from ...domain.entities import EntryPart
from ..deps import (
    CurrentUserDep,
    SessionDep,
    get_add_entry_example,
    get_add_entry_gloss,
    get_add_entry_reading,
    get_add_entry_sense,
    get_add_entry_spelling,
    get_edit_entry_example,
    get_edit_entry_gloss,
    get_get_library_entry,
    get_list_collections_of_entry,
    get_remove_entry_example,
    get_remove_entry_from_library,
    get_remove_entry_gloss,
    get_remove_entry_reading,
    get_remove_entry_sense,
    get_remove_entry_spelling,
    get_set_entry_active,
    get_set_entry_notes,
    get_set_entry_part_enabled,
    get_set_sense_notes,
)
from ..schemas import (
    ActiveRequest,
    CollectionResponse,
    EnabledRequest,
    ExampleRequest,
    MeaningTextRequest,
    NewGlossRequest,
    NotesRequest,
    PracticeEntryResponse,
    ReadingRequest,
    SpellingRequest,
)

_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Missing or invalid token."},
    status.HTTP_404_NOT_FOUND: {
        "description": "Not in the user's library, or no such nested item."
    },
}
_ORIGINAL: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {
        "description": "Dictionary data (a spelling, reading, sense, meaning or "
        "example): it can only be disabled. Or the word's last reading, or the "
        "sense's last meaning."
    }
}

router = APIRouter(prefix="/library/entries", tags=["library"], responses=_RESPONSES)


class EntryPartPath(StrEnum):
    """The parts that can be enabled or disabled, as they appear in the URL."""

    KANJI_READINGS = "kanji-readings"
    READINGS = "readings"
    SENSES = "senses"
    GLOSSES = "glosses"
    EXAMPLES = "examples"


_PARTS: dict[EntryPartPath, EntryPart] = {
    EntryPartPath.KANJI_READINGS: "kanji_readings",
    EntryPartPath.READINGS: "readings",
    EntryPartPath.SENSES: "senses",
    EntryPartPath.GLOSSES: "glosses",
    EntryPartPath.EXAMPLES: "examples",
}


@router.get("/{entry_id}", response_model=PracticeEntryResponse)
def get_entry(
    entry_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[GetLibraryEntry, Depends(get_get_library_entry)],
) -> PracticeEntryResponse:
    """The user's copy of an entry, with its practice state and notes."""
    entry = use_case.execute(user.id, entry_id)
    session.commit()  # persists the user if this request created it
    return PracticeEntryResponse.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_entry(
    entry_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveEntryFromLibrary, Depends(get_remove_entry_from_library)],
) -> None:
    """Remove the entry from the library and from every collection."""
    use_case.execute(user.id, entry_id)
    session.commit()


@router.get("/{entry_id}/collections", response_model=list[CollectionResponse])
def list_entry_collections(
    entry_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[ListCollectionsOfEntry, Depends(get_list_collections_of_entry)],
) -> list[CollectionResponse]:
    """The collections (tags) the entry is in, by name."""
    collections = use_case.execute(user.id, entry_id)
    session.commit()
    return [CollectionResponse.model_validate(c) for c in collections]


@router.put("/{entry_id}/active", response_model=PracticeEntryResponse)
def set_active(
    entry_id: int,
    body: ActiveRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetEntryActive, Depends(get_set_entry_active)],
) -> PracticeEntryResponse:
    """Activate or deactivate the entry (inactive ones aren't practised)."""
    entry = use_case.execute(user.id, entry_id, body.active)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.put("/{entry_id}/notes", response_model=PracticeEntryResponse)
def set_notes(
    entry_id: int,
    body: NotesRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetEntryNotes, Depends(get_set_entry_notes)],
) -> PracticeEntryResponse:
    """Replace the entry's general note."""
    entry = use_case.execute(user.id, entry_id, body.notes)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.put("/{entry_id}/senses/{sense_id}/notes", response_model=PracticeEntryResponse)
def set_sense_notes(
    entry_id: int,
    sense_id: int,
    body: NotesRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetSenseNotes, Depends(get_set_sense_notes)],
) -> PracticeEntryResponse:
    """Replace the note on one sense."""
    entry = use_case.execute(user.id, entry_id, sense_id, body.notes)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.put(
    "/{entry_id}/{part}/{item_id}/enabled", response_model=PracticeEntryResponse
)
def set_enabled(
    entry_id: int,
    part: EntryPartPath,
    item_id: int,
    body: EnabledRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[SetEntryPartEnabled, Depends(get_set_entry_part_enabled)],
) -> PracticeEntryResponse:
    """Show or hide one spelling, reading, sense, meaning or example by its `id`.

    A disabled sense hides its meanings and examples; their own flags are
    kept for when it's enabled again.
    """
    entry = use_case.execute(user.id, entry_id, _PARTS[part], item_id, body.enabled)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.post(
    "/{entry_id}/senses",
    response_model=PracticeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_sense(
    entry_id: int,
    body: NewGlossRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddEntrySense, Depends(get_add_entry_sense)],
) -> PracticeEntryResponse:
    """Add a sense of the user's own at the end, with its first meaning."""
    entry = use_case.execute(user.id, entry_id, body.text, body.lang)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.delete(
    "/{entry_id}/senses/{sense_id}",
    response_model=PracticeEntryResponse,
    responses=_ORIGINAL,
)
def remove_sense(
    entry_id: int,
    sense_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveEntrySense, Depends(get_remove_entry_sense)],
) -> PracticeEntryResponse:
    """Remove one of the user's own senses, with its meanings and examples."""
    entry = use_case.execute(user.id, entry_id, sense_id)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.post(
    "/{entry_id}/senses/{sense_id}/glosses",
    response_model=PracticeEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid, or not in the language of the sense's meanings."
        }
    },
)
def add_gloss(
    entry_id: int,
    sense_id: int,
    body: NewGlossRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddEntryGloss, Depends(get_add_entry_gloss)],
) -> PracticeEntryResponse:
    """Add a meaning of the user's own at the end of the sense.

    In the sense's language: a sense's meanings are all in one language.
    """
    entry = use_case.execute(user.id, entry_id, sense_id, body.text, body.lang)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.put(
    "/{entry_id}/glosses/{gloss_id}",
    response_model=PracticeEntryResponse,
    responses=_ORIGINAL,
)
def edit_gloss(
    entry_id: int,
    gloss_id: int,
    body: MeaningTextRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[EditEntryGloss, Depends(get_edit_entry_gloss)],
) -> PracticeEntryResponse:
    """Change the text of one of the user's own meanings."""
    entry = use_case.execute(user.id, entry_id, gloss_id, body.text)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.delete(
    "/{entry_id}/glosses/{gloss_id}",
    response_model=PracticeEntryResponse,
    responses=_ORIGINAL,
)
def remove_gloss(
    entry_id: int,
    gloss_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveEntryGloss, Depends(get_remove_entry_gloss)],
) -> PracticeEntryResponse:
    """Remove one of the user's own meanings."""
    entry = use_case.execute(user.id, entry_id, gloss_id)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.post(
    "/{entry_id}/kanji-readings",
    response_model=PracticeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_spelling(
    entry_id: int,
    body: SpellingRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddEntrySpelling, Depends(get_add_entry_spelling)],
) -> PracticeEntryResponse:
    """Add a written form of the user's own at the end."""
    entry = use_case.execute(user.id, entry_id, body.kanji)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.delete(
    "/{entry_id}/kanji-readings/{spelling_id}",
    response_model=PracticeEntryResponse,
    responses=_ORIGINAL,
)
def remove_spelling(
    entry_id: int,
    spelling_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveEntrySpelling, Depends(get_remove_entry_spelling)],
) -> PracticeEntryResponse:
    """Remove one of the user's own written forms."""
    entry = use_case.execute(user.id, entry_id, spelling_id)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.post(
    "/{entry_id}/readings",
    response_model=PracticeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_reading(
    entry_id: int,
    body: ReadingRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddEntryReading, Depends(get_add_entry_reading)],
) -> PracticeEntryResponse:
    """Add a reading (kana) of the user's own at the end."""
    entry = use_case.execute(user.id, entry_id, body.text)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.delete(
    "/{entry_id}/readings/{reading_id}",
    response_model=PracticeEntryResponse,
    responses=_ORIGINAL,
)
def remove_reading(
    entry_id: int,
    reading_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveEntryReading, Depends(get_remove_entry_reading)],
) -> PracticeEntryResponse:
    """Remove one of the user's own readings; a word keeps at least one (409)."""
    entry = use_case.execute(user.id, entry_id, reading_id)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.post(
    "/{entry_id}/senses/{sense_id}/examples",
    response_model=PracticeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_example(
    entry_id: int,
    sense_id: int,
    body: ExampleRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[AddEntryExample, Depends(get_add_entry_example)],
) -> PracticeEntryResponse:
    """Add an example sentence of the user's own at the end of the sense."""
    entry = use_case.execute(
        user.id, entry_id, sense_id, body.japanese, body.translation, body.lang
    )
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.put(
    "/{entry_id}/examples/{example_id}",
    response_model=PracticeEntryResponse,
    responses=_ORIGINAL,
)
def edit_example(
    entry_id: int,
    example_id: int,
    body: ExampleRequest,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[EditEntryExample, Depends(get_edit_entry_example)],
) -> PracticeEntryResponse:
    """Rewrite one of the user's own examples.

    Replaces the Japanese sentence and the translation in `lang`; translations
    in other languages are kept.
    """
    entry = use_case.execute(
        user.id, entry_id, example_id, body.japanese, body.translation, body.lang
    )
    session.commit()
    return PracticeEntryResponse.model_validate(entry)


@router.delete(
    "/{entry_id}/examples/{example_id}",
    response_model=PracticeEntryResponse,
    responses=_ORIGINAL,
)
def remove_example(
    entry_id: int,
    example_id: int,
    user: CurrentUserDep,
    session: SessionDep,
    use_case: Annotated[RemoveEntryExample, Depends(get_remove_entry_example)],
) -> PracticeEntryResponse:
    """Remove one of the user's own examples."""
    entry = use_case.execute(user.id, entry_id, example_id)
    session.commit()
    return PracticeEntryResponse.model_validate(entry)
