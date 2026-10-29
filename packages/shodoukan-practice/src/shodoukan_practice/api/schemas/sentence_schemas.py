"""Request and response models for the sentences of the user's library."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ...application.queries import MAX_ANALYZED_SENTENCES
from .library_schemas import Origin, SentenceText

# Words a reviewed sentence may mark: a long sentence has a few dozen.
MAX_SENTENCE_WORDS = 50

Offset = Annotated[int, Field(ge=0, le=500)]


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SentenceRequest(BaseModel):
    """A sentence of the user's own and its translation in one language."""

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


class NewSentenceRequest(SentenceRequest):
    entry_id: int | None = Field(
        default=None,
        description="One of the user's words to link; its gap is found where "
        "it is in the sentence.",
    )
    sense_id: int | None = Field(default=None, description="The word's sense.")


class WordRequest(BaseModel):
    start: Offset | None = Field(default=None, description="Start of its span.")
    end: Offset | None = Field(default=None, description="End of its span.")
    entry_id: int | None = Field(default=None, description="The library word.")
    sense_id: int | None = None

    @model_validator(mode="after")
    def _check(self) -> "WordRequest":
        if (self.start is None) != (self.end is None):
            raise ValueError("a span has a start and an end, or neither")
        if self.start is None and self.entry_id is None:
            raise ValueError("a word without a span must be linked")
        return self


class SpanRequest(BaseModel):
    start: Offset
    end: Offset


class LinkRequest(BaseModel):
    entry_id: int | None = Field(description="Null unlinks the word.")
    sense_id: int | None = None


class CorrectionRequest(BaseModel):
    lemma: str = Field(min_length=1, max_length=100)
    reading: str = Field(min_length=1, max_length=100)


class SentenceDraftRequest(SentenceRequest):
    words: list[WordRequest] = Field(default=[], max_length=MAX_SENTENCE_WORDS)


class SentenceBatchRequest(BaseModel):
    sentences: list[SentenceDraftRequest] = Field(
        min_length=1, max_length=MAX_ANALYZED_SENTENCES
    )


class AnalyzeRequest(BaseModel):
    texts: list[SentenceText] = Field(min_length=1, max_length=MAX_ANALYZED_SENTENCES)


class InflectionResponse(_Response):
    endings: list[str]
    form: str | None

    @field_validator("endings", mode="before")
    @classmethod
    def _list(cls, value: object) -> object:
        return list(value) if isinstance(value, tuple) else value


class SentenceWordResponse(_Response):
    id: int
    start: int | None
    end: int | None
    lemma: str | None
    reading: str | None
    pos: list[str]
    inflection: InflectionResponse | None
    entry_id: int | None
    sense_id: int | None


class SentenceTranslationResponse(_Response):
    lang: str
    text: str


class SentenceResponse(_Response):
    id: int
    text: str
    translations: list[SentenceTranslationResponse]
    words: list[SentenceWordResponse]
    is_active: bool
    notes: str | None
    origin: Origin
    created_at: datetime
    updated_at: datetime


class SentencePageResponse(_Response):
    items: list[SentenceResponse]
    total: int
    limit: int
    offset: int


class MorphemeResponse(_Response):
    surface: str
    lemma: str
    reading: str
    pos: list[str]
    start: int
    end: int

    @field_validator("pos", mode="before")
    @classmethod
    def _list(cls, value: object) -> object:
        return list(value) if isinstance(value, tuple) else value


class WordProposalResponse(_Response):
    start: int
    end: int
    form: str = Field(description="The library form it was found by.")
    entry_ids: list[int] = Field(description="The user's words with that form.")
    certain: bool = Field(
        description="Found by a spelling with kanji; false for a kana-only match "
        "(はし), to confirm."
    )

    @field_validator("entry_ids", mode="before")
    @classmethod
    def _list(cls, value: object) -> object:
        return list(value) if isinstance(value, tuple) else value


class SentenceProposalResponse(_Response):
    text: str
    morphemes: list[MorphemeResponse]
    words: list[WordProposalResponse]
