from datetime import datetime

from shodoukan_practice.domain.entities import (
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

NOW = datetime(2026, 1, 1)


def make_entry() -> PracticeEntry:
    return PracticeEntry(
        id=1,
        user_id=1,
        source_entry_id=1000001,
        kanji_readings=[
            PracticeKanjiReading(id=1, kanji="食べる", info=[]),
        ],
        readings=[
            PracticeReading(
                id=1, text="たべる", no_kanji=False, info=[], restricted_to=[],
            ),
        ],
        senses=[
            PracticeSense(
                id=1,
                pos=["v1"],
                misc=[],
                dialects=[],
                info=[],
                glosses=[
                    PracticeGloss(id=1, text="to eat", lang="eng", type=None),
                    PracticeGloss(
                        id=None, text="jamar (coloquial)", lang="spa",
                        type=None, origin="added",
                    ),
                ],
                examples=[
                    PracticeExample(
                        id=1,
                        text="",
                        sentences=[
                            PracticeExampleSentence(lang="jpn", text="ご飯を食べる。"),
                        ],
                    ),
                ],
            ),
        ],
        jlpt=5,
        is_common=True,
        created_at=NOW,
        updated_at=NOW,
    )


def make_kanji() -> PracticeKanji:
    return PracticeKanji(
        id=1,
        user_id=1,
        literal="食",
        grade=2,
        stroke_count=9,
        freq=316,
        jlpt=4,
        on_readings=[PracticeReadingItem(id=1, text="ショク")],
        kun_readings=[PracticeReadingItem(id=2, text="た.べる")],
        nanori=[],
        meanings=[
            PracticeKanjiMeaning(id=1, text="eat", lang="en"),
            PracticeKanjiMeaning(
                id=None, text="food (extra)", lang="en", origin="added",
            ),
        ],
        created_at=NOW,
        updated_at=NOW,
    )


def test_practice_entry_shape_and_defaults():
    entry = make_entry()
    assert entry.is_active is True
    assert entry.senses[0].glosses[0].enabled is True
    assert entry.senses[0].glosses[0].origin == "imported"
    assert entry.senses[0].glosses[1].origin == "added"


def test_practice_entry_serializes_round_trip():
    entry = make_entry()
    dumped = entry.model_dump()
    assert PracticeEntry.model_validate(dumped) == entry


def test_practice_kanji_shape_and_defaults():
    kanji = make_kanji()
    assert kanji.is_active is True
    assert kanji.meanings[0].origin == "imported"
    assert kanji.meanings[1].origin == "added"


def test_practice_kanji_serializes_round_trip():
    kanji = make_kanji()
    dumped = kanji.model_dump()
    assert PracticeKanji.model_validate(dumped) == kanji
