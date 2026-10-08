"""Request and response models for the user's library.

Responses mirror the domain entities but are their own models, so the API
contract doesn't change when the domain does. Datetimes are aware UTC and
serialize as ISO 8601 with offset (`...Z`).
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from ...domain.entities import NOTES_MAX_LENGTH

Origin = Literal["imported", "added"]


# Collections to put the item in while importing it; a handful in practice.
MAX_IMPORT_COLLECTIONS = 50


class ImportEntryRequest(BaseModel):
    entry_id: int = Field(description="Dictionary entry id (shodoukan `Entry.id`).")
    collection_ids: list[int] = Field(
        default_factory=list,
        max_length=MAX_IMPORT_COLLECTIONS,
        description="Entry collections to put it in too (optional).",
    )


class ImportKanjiRequest(BaseModel):
    literal: str = Field(
        min_length=1, max_length=1, description="The kanji character, e.g. 食."
    )
    collection_ids: list[int] = Field(
        default_factory=list,
        max_length=MAX_IMPORT_COLLECTIONS,
        description="Kanji collections to put it in too (optional).",
    )


MeaningText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class ActiveRequest(BaseModel):
    active: bool


class EnabledRequest(BaseModel):
    enabled: bool


class NotesRequest(BaseModel):
    notes: str | None = Field(
        max_length=NOTES_MAX_LENGTH, description="Blank or null removes the note."
    )


class NewGlossRequest(BaseModel):
    text: MeaningText
    lang: str = Field(
        pattern="^[a-z]{3}$",
        description="ISO 639-2, like the entry's glosses (e.g. `eng`, `spa`).",
    )


class NewKanjiMeaningRequest(BaseModel):
    text: MeaningText
    lang: str = Field(
        pattern="^[a-z]{2}$",
        description="ISO 639-1, like the kanji's meanings (e.g. `en`, `es`).",
    )


class MeaningTextRequest(BaseModel):
    text: MeaningText


SentenceText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class ExampleRequest(BaseModel):
    japanese: SentenceText
    translation: str | None = Field(
        default=None, max_length=500, description="Blank or null for none."
    )
    lang: str = Field(
        pattern="^[a-z]{3}$",
        description="The translation's language, ISO 639-2 (e.g. `eng`, `spa`); "
        "not `jpn`, the sentence's own.",
    )

    @field_validator("lang")
    @classmethod
    def _not_japanese(cls, lang: str) -> str:
        if lang == "jpn":
            raise ValueError("the translation can't be in Japanese")
        return lang


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
    notes: str | None
    enabled: bool
    origin: Origin


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
    notes: str | None
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
    notes: str | None
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
