"""Domain entities used across the practice infrastructure tests."""

from datetime import UTC, datetime

from shodoukan_practice.domain.entities import (
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeExample,
    PracticeExampleSentence,
    PracticeGloss,
    PracticeKanji,
    PracticeKanjiMeaning,
    PracticeKanjiReading,
    PracticeReading,
    PracticeReadingItem,
    PracticeSense,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make_entry(
    user_id: int, source_entry_id: int = 1000001, *, is_active: bool = True
) -> PracticeEntry:
    return PracticeEntry(
        id=None,
        user_id=user_id,
        source_entry_id=source_entry_id,
        kanji_readings=[PracticeKanjiReading(id=None, kanji="食べる", info=[])],
        readings=[
            PracticeReading(
                id=None, text="たべる", no_kanji=False, info=[], restricted_to=[]
            ),
            PracticeReading(
                id=None, text="くう", no_kanji=False, info=["ok"], restricted_to=[]
            ),
        ],
        senses=[
            PracticeSense(
                id=None,
                pos=["v1"],
                misc=[],
                dialects=[],
                info=[],
                glosses=[
                    PracticeGloss(id=None, text="to eat", lang="eng", type=None),
                    PracticeGloss(id=None, text="comer", lang="spa", type=None),
                ],
                examples=[
                    PracticeExample(
                        id=None,
                        text="",
                        sentences=[
                            PracticeExampleSentence(lang="jpn", text="ご飯を食べる。"),
                            PracticeExampleSentence(lang="eng", text="Eat rice."),
                        ],
                    ),
                ],
            ),
        ],
        jlpt=5,
        is_common=True,
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )


def make_kanji(
    user_id: int, literal: str = "食", *, is_active: bool = True
) -> PracticeKanji:
    return PracticeKanji(
        id=None,
        user_id=user_id,
        literal=literal,
        grade=2,
        stroke_count=9,
        freq=316,
        jlpt=4,
        on_readings=[PracticeReadingItem(id=None, text="ショク")],
        kun_readings=[
            PracticeReadingItem(id=None, text="た.べる"),
            PracticeReadingItem(id=None, text="く.う"),
        ],
        nanori=[],
        meanings=[
            PracticeKanjiMeaning(id=None, text="eat", lang="en"),
            PracticeKanjiMeaning(id=None, text="food", lang="en", origin="added"),
        ],
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )


def make_entry_collection(user_id: int, name: str = "verbs") -> EntryCollection:
    return EntryCollection(
        id=None, user_id=user_id, name=name, created_at=NOW, updated_at=NOW
    )


def make_kanji_collection(user_id: int, name: str = "N5") -> KanjiCollection:
    return KanjiCollection(
        id=None, user_id=user_id, name=name, created_at=NOW, updated_at=NOW
    )
