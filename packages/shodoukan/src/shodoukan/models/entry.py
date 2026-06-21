from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class Gloss(BaseModel):
    id: int
    text: str
    type: str | None
    lang: str


class CrossReference(BaseModel):
    reference: str
    reading: str | None
    sense_idx: int | None


class ExampleSentence(BaseModel):
    lang: str
    text: str


class Example(BaseModel):
    id: int
    source_name: str
    source_id: str | None
    text: str
    sentences: list[ExampleSentence]


class Sense(BaseModel):
    id: int
    pos: list[str]
    misc: list[str]
    dialects: list[str]
    info: list[str]
    glosses: list[Gloss]
    cross_references: list[CrossReference]
    examples: list[Example]


class Reading(BaseModel):
    id: int
    text: str
    no_kanji: bool
    priority: list[str]
    info: list[str]
    restricted_to: list[str]


class KanjiReading(BaseModel):
    id: int
    kanji: str
    priority: list[str]
    info: list[str]


class ScoreBreakdown(BaseModel):
    freq: int | None = None
    jlpt_bonus: int | None = None
    exact_match: bool | None = None
    fts_rank: float | None = None
    sense_pos: int | None = None
    total_senses: int | None = None
    composite: float | None = None


class Entry(BaseModel):
    id: int
    kanji_readings: list[KanjiReading]
    readings: list[Reading]
    senses: list[Sense]
    jlpt: int | None = None
    is_common: bool = False
    score: ScoreBreakdown | None = None


class EntryKanjiLink(BaseModel):
    literal: str
