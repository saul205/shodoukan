"""The shodoukan dictionary: public search."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ...application.queries import SearchDictionary
from ..deps import get_search_dictionary
from ..schemas import DictionarySearchResponse

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
