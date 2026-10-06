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


class KanjiStroke(BaseModel):
    """One stroke of a KanjiVG drawing, in its coordinate space (a 109-unit square)."""

    path: str
    """SVG path data of the stroke's centre line, drawn with a round stroke."""
    label: tuple[float, float] | None
    """Where KanjiVG places the stroke's number, if it has one."""


class KanjiStrokes(BaseModel):
    """A character's strokes in writing order (KanjiVG, Japanese stroke order)."""

    literal: str
    strokes: list[KanjiStroke]
