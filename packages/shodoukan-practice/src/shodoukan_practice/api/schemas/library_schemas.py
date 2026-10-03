"""Request and response models for the user's library.

Responses mirror the domain entities but are their own models, so the API
contract doesn't change when the domain does. Datetimes are aware UTC and
serialize as ISO 8601 with offset (`...Z`).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Origin = Literal["imported", "added"]


class ImportEntryRequest(BaseModel):
    entry_id: int = Field(description="Dictionary entry id (shodoukan `Entry.id`).")


class ImportKanjiRequest(BaseModel):
    literal: str = Field(
        min_length=1, max_length=1, description="The kanji character, e.g. 食."
    )


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GlossResponse(_Response):
    id: int
    text: str
    lang: str
    type: str | None
    enabled: bool
    origin: Origin


class ExampleSentenceResponse(_Response):
    lang: str
    text: str


class ExampleResponse(_Response):
    id: int
    text: str
    sentences: list[ExampleSentenceResponse]
    enabled: bool
    origin: Origin


class SenseResponse(_Response):
    id: int
    pos: list[str]
    misc: list[str]
    dialects: list[str]
    info: list[str]
    glosses: list[GlossResponse]
    examples: list[ExampleResponse]


class ReadingResponse(_Response):
    id: int
    text: str
    no_kanji: bool
    info: list[str]
    restricted_to: list[str]
    enabled: bool


class KanjiReadingResponse(_Response):
    id: int
    kanji: str
    info: list[str]
    enabled: bool


class PracticeEntryResponse(_Response):
    id: int
    source_entry_id: int
    kanji_readings: list[KanjiReadingResponse]
    readings: list[ReadingResponse]
    senses: list[SenseResponse]
    jlpt: int | None
    is_common: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PracticeEntryPageResponse(_Response):
    items: list[PracticeEntryResponse]
    total: int  # items matching the request, across every page
    limit: int
    offset: int


class ReadingItemResponse(_Response):
    id: int
    text: str
    enabled: bool


class KanjiMeaningResponse(_Response):
    id: int
    text: str
    lang: str
    enabled: bool
    origin: Origin


class PracticeKanjiResponse(_Response):
    id: int
    literal: str
    grade: int | None
    stroke_count: int
    freq: int | None
    jlpt: int | None
    on_readings: list[ReadingItemResponse]
    kun_readings: list[ReadingItemResponse]
    nanori: list[ReadingItemResponse]
    meanings: list[KanjiMeaningResponse]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PracticeKanjiPageResponse(_Response):
    items: list[PracticeKanjiResponse]
    total: int  # items matching the request, across every page
    limit: int
    offset: int


class ImportedEntryResponse(BaseModel):
    source_entry_id: int
    id: int  # the practice entry


class ImportedKanjiResponse(BaseModel):
    literal: str
    id: int  # the practice kanji


class ImportStatusResponse(BaseModel):
    """Which of the asked-about dictionary items are in the user's library.

    Only imported items are listed; anything asked about and missing here
    isn't imported.
    """

    entries: list[ImportedEntryResponse]
    kanji: list[ImportedKanjiResponse]
