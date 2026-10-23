"""The shodoukan dictionary: public search and entry and kanji details."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Response, status

from ...application.queries import (
    GetDictionaryEntry,
    GetDictionaryKanji,
    GetDictionaryKanjiStrokes,
    ListEntriesForKanji,
    ListKanjiForEntry,
    SearchDictionary,
)
from ..deps import (
    get_get_dictionary_entry,
    get_get_dictionary_kanji,
    get_get_dictionary_kanji_strokes,
    get_list_entries_for_kanji,
    get_list_kanji_for_entry,
    get_search_dictionary,
)
from ..schemas import (
    DictionaryEntryPageResponse,
    DictionaryEntryResponse,
    DictionaryKanjiResponse,
    DictionaryKanjiStrokesResponse,
    DictionarySearchResponse,
)

KanjiLiteral = Annotated[str, Path(min_length=1, max_length=1)]

router = APIRouter(prefix="/dictionary", tags=["dictionary"])


@router.get("/search", response_model=DictionarySearchResponse)
def search(
    use_case: Annotated[SearchDictionary, Depends(get_search_dictionary)],
    q: Annotated[
        str,
        Query(min_length=1, description="Kanji, kana, Hepburn romaji or a meaning."),
    ],
    lang: Annotated[
        str, Query(description="ISO 639-1 language meanings are matched in.")
    ] = "en",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DictionarySearchResponse:
    """Search the dictionary. Public: no sign-in needed.

    Same detection and ranking as shodoukan-api's `/search`. To know which
    results the user already has, ask `GET /library/imported` in parallel.
    """
    result = use_case.execute(q, lang=lang, limit=limit, offset=offset)
    return DictionarySearchResponse.model_validate(result)


_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"description": "Not in the dictionary."}
}


@router.get(
    "/entries/{entry_id}", response_model=DictionaryEntryResponse, responses=_NOT_FOUND
)
def get_entry(
    entry_id: int,
    use_case: Annotated[GetDictionaryEntry, Depends(get_get_dictionary_entry)],
) -> DictionaryEntryResponse:
    """One dictionary entry. Its `id` is what `POST /library/entries` takes."""
    return DictionaryEntryResponse.model_validate(use_case.execute(entry_id))


@router.get(
    "/entries/{entry_id}/kanji",
    response_model=list[DictionaryKanjiResponse],
    responses=_NOT_FOUND,
)
def get_entry_kanji(
    entry_id: int,
    use_case: Annotated[ListKanjiForEntry, Depends(get_list_kanji_for_entry)],
) -> list[DictionaryKanjiResponse]:
    """The kanji the entry is written with; empty for kana-only words."""
    return [
        DictionaryKanjiResponse.model_validate(k) for k in use_case.execute(entry_id)
    ]


@router.get(
    "/kanji/{literal}", response_model=DictionaryKanjiResponse, responses=_NOT_FOUND
)
def get_kanji(
    literal: KanjiLiteral,
    use_case: Annotated[GetDictionaryKanji, Depends(get_get_dictionary_kanji)],
) -> DictionaryKanjiResponse:
    """One dictionary kanji. Its `literal` is what `POST /library/kanji` takes."""
    return DictionaryKanjiResponse.model_validate(use_case.execute(literal))


# Stroke order only changes with a new dictionary release.
_STROKES_CACHE_CONTROL = "public, max-age=86400"


@router.get(
    "/kanji/{literal}/strokes",
    response_model=DictionaryKanjiStrokesResponse,
    responses=_NOT_FOUND,
)
def get_kanji_strokes(
    literal: KanjiLiteral,
    response: Response,
    use_case: Annotated[
        GetDictionaryKanjiStrokes, Depends(get_get_dictionary_kanji_strokes)
    ],
) -> DictionaryKanjiStrokesResponse:
    """Stroke order (KanjiVG), for any character with a drawing."""
    strokes = use_case.execute(literal)
    response.headers["Cache-Control"] = _STROKES_CACHE_CONTROL
    return DictionaryKanjiStrokesResponse.model_validate(strokes)


@router.get(
    "/kanji/{literal}/entries",
    response_model=DictionaryEntryPageResponse,
    responses=_NOT_FOUND,
)
def get_kanji_entries(
    literal: KanjiLiteral,
    use_case: Annotated[ListEntriesForKanji, Depends(get_list_entries_for_kanji)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DictionaryEntryPageResponse:
    """A page of the words written with the kanji, ranked like the search."""
    page = use_case.execute(literal, limit=limit, offset=offset)
    return DictionaryEntryPageResponse.model_validate(page)
