"""Response models for dictionary search.

Same shape as shodoukan-api's `GET /search` (`entries` page + `kanji`), so
frontend components can render either, but owned by this API so each app
can evolve on its own.
"""

from pydantic import BaseModel, ConfigDict


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DictionaryGlossResponse(_Response):
    text: str
    lang: str
    type: str | None


class DictionaryCrossReferenceResponse(_Response):
    reference: str
    reading: str | None
    sense_index: int | None


class DictionaryExampleSentenceResponse(_Response):
    lang: str
    text: str


class DictionaryExampleResponse(_Response):
    text: str
    sentences: list[DictionaryExampleSentenceResponse]


class DictionarySenseResponse(_Response):
    pos: list[str]
    misc: list[str]
    dialects: list[str]
    info: list[str]
    glosses: list[DictionaryGlossResponse]
    cross_references: list[DictionaryCrossReferenceResponse]
    examples: list[DictionaryExampleResponse]


class DictionaryReadingResponse(_Response):
    text: str
    no_kanji: bool
    info: list[str]
    restricted_to: list[str]


class DictionaryKanjiReadingResponse(_Response):
    kanji: str
    info: list[str]


class DictionaryEntryResponse(_Response):
    id: int
    kanji_readings: list[DictionaryKanjiReadingResponse]
    readings: list[DictionaryReadingResponse]
    senses: list[DictionarySenseResponse]
    jlpt: int | None
    is_common: bool


class DictionaryKanjiMeaningResponse(_Response):
    text: str
    lang: str


class DictionaryKanjiResponse(_Response):
    literal: str
    grade: int | None
    stroke_count: int
    freq: int | None
    jlpt: int | None
    on_readings: list[str]
    kun_readings: list[str]
    nanori: list[str]
    meanings: list[DictionaryKanjiMeaningResponse]


class DictionaryKanjiStrokeResponse(_Response):
    path: str
    label: tuple[float, float] | None


class DictionaryKanjiStrokesResponse(_Response):
    """Same shape as shodoukan-api's `GET /kanji/{literal}/strokes`."""

    literal: str
    strokes: list[DictionaryKanjiStrokeResponse]


class DictionaryEntryPageResponse(_Response):
    items: list[DictionaryEntryResponse]
    total: int
    limit: int
    offset: int


class DictionarySearchResponse(_Response):
    entries: DictionaryEntryPageResponse
    kanji: list[DictionaryKanjiResponse]
