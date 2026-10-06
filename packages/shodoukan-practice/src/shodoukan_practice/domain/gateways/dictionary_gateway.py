"""Port for reading the shodoukan dictionary.

The dictionary is an external, read-only source. The gateway offers:

- **Snapshots for import:** fresh practice entities ready to be stored in a
  user's library (`new_practice_entry`, `new_practice_kanji`).
- **Search and details:** dictionary results, single entries and kanji as
  read models (`Dictionary*` below), the practice app's own contract for
  showing dictionary data. They're frozen,
  carry no practice state, and keep the domain independent of the
  dictionary's models.
"""

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ..entities import PracticeEntry, PracticeKanji


class _ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class DictionaryGloss(_ReadModel):
    text: str
    lang: str
    type: str | None


class DictionaryCrossReference(_ReadModel):
    reference: str
    reading: str | None
    sense_index: int | None


class DictionaryExampleSentence(_ReadModel):
    lang: str
    text: str


class DictionaryExample(_ReadModel):
    text: str
    sentences: list[DictionaryExampleSentence]


class DictionarySense(_ReadModel):
    pos: list[str]
    misc: list[str]
    dialects: list[str]
    info: list[str]
    glosses: list[DictionaryGloss]
    cross_references: list[DictionaryCrossReference]
    examples: list[DictionaryExample]


class DictionaryReading(_ReadModel):
    text: str
    no_kanji: bool
    info: list[str]
    restricted_to: list[str]


class DictionaryKanjiReading(_ReadModel):
    """Kanji spelling of a word entry (e.g. "食べる")."""

    kanji: str
    info: list[str]


class DictionaryEntry(_ReadModel):
    id: int  # what POST /library/entries takes as `entry_id`
    kanji_readings: list[DictionaryKanjiReading]
    readings: list[DictionaryReading]
    senses: list[DictionarySense]
    jlpt: int | None
    is_common: bool


class DictionaryKanjiMeaning(_ReadModel):
    text: str
    lang: str


class DictionaryKanji(_ReadModel):
    literal: str
    grade: int | None
    stroke_count: int
    freq: int | None
    jlpt: int | None
    on_readings: list[str]
    kun_readings: list[str]
    nanori: list[str]
    meanings: list[DictionaryKanjiMeaning]


class DictionaryKanjiStroke(_ReadModel):
    """One stroke, in KanjiVG's 109-unit square: its centre line and number."""

    path: str
    label: tuple[float, float] | None


class DictionaryKanjiStrokes(_ReadModel):
    """A character's strokes in Japanese writing order (KanjiVG)."""

    literal: str
    strokes: list[DictionaryKanjiStroke]


class DictionaryEntryPage(_ReadModel):
    items: list[DictionaryEntry]
    total: int
    limit: int
    offset: int


class DictionarySearchResult(_ReadModel):
    """A page of matching entries, plus the kanji related to the query."""

    entries: DictionaryEntryPage
    kanji: list[DictionaryKanji]


class DictionaryGateway(Protocol):
    def new_practice_entry(
        self, source_entry_id: int, user_id: UUID
    ) -> PracticeEntry | None:
        """Snapshot of dictionary entry `source_entry_id` for `user_id`.

        `None` if the dictionary has no such entry. The result isn't stored:
        ids are `None`, everything is enabled and `origin="imported"`.
        """
        ...

    def new_practice_kanji(self, literal: str, user_id: UUID) -> PracticeKanji | None:
        """Snapshot of dictionary kanji `literal` for `user_id`, or `None`."""
        ...

    def search(
        self, query: str, lang: str, limit: int, offset: int
    ) -> DictionarySearchResult:
        """Dictionary search: kanji, kana, Hepburn romaji or a meaning.

        The query kind is detected and results are ranked by the dictionary.
        `lang` (ISO 639-1) is the language meanings are matched in; results
        keep every language.
        """
        ...

    def get_entry(self, entry_id: int) -> DictionaryEntry | None:
        """Dictionary entry `entry_id`, or `None`."""
        ...

    def get_kanji(self, literal: str) -> DictionaryKanji | None:
        """Dictionary kanji `literal`, or `None`."""
        ...

    def kanji_strokes(self, literal: str) -> DictionaryKanjiStrokes | None:
        """Stroke order of `literal`, or `None` if there's no drawing for it.

        Any character with a drawing has one, even if it isn't a dictionary
        kanji (kana, for instance).
        """
        ...

    def entries_for_kanji(
        self, literal: str, limit: int, offset: int
    ) -> DictionaryEntryPage:
        """A page of the entries written with kanji `literal`, ranked."""
        ...

    def kanji_for_entry(self, entry_id: int) -> list[DictionaryKanji]:
        """The kanji in entry `entry_id`'s spellings; empty if it has none."""
        ...
