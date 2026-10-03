"""Query parameters for searching the library, shared by its list endpoints."""

from typing import Annotated

from fastapi import Query

SearchText = Annotated[
    str | None,
    Query(
        max_length=100,
        description=(
            "Search by spelling or reading (kanji, kana, or romaji, converted to"
            " kana) and by meaning. Best match first; blank lists everything."
        ),
    ),
]

MeaningLang = Annotated[
    str | None,
    Query(
        max_length=8,
        description=(
            "Language of the meanings to search, as the items store it: ISO 639-2"
            " for entries (`eng`), ISO 639-1 for kanji (`en`). Any if omitted."
        ),
    ),
]

NotInCollection = Annotated[
    int | None,
    Query(
        ge=1,
        description=(
            "Leave out the items of this collection of the user's (what can still"
            " be added to it)."
        ),
    ),
]
