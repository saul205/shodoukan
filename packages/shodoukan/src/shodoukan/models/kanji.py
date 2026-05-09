from pydantic import BaseModel


class KanjiMeaning(BaseModel):
    text: str
    lang: str


class Kanji(BaseModel):
    literal: str
    grade: int | None
    stroke_count: int
    freq: int | None
    jlpt: int | None
    on_readings: list[str]
    kun_readings: list[str]
    nanori: list[str]
    meanings: list[KanjiMeaning]
