from datetime import UTC, datetime

from shodoukan_practice.domain.entities import (
    PracticeKanji,
    PracticeKanjiMeaning,
    PracticeReadingItem,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


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
                id=None,
                text="food (extra)",
                lang="en",
                origin="added",
            ),
        ],
        created_at=NOW,
        updated_at=NOW,
    )


def test_practice_kanji_shape_and_defaults() -> None:
    kanji = make_kanji()
    assert kanji.is_active is True
    assert kanji.meanings[0].origin == "imported"
    assert kanji.meanings[1].origin == "added"


def test_practice_kanji_serializes_round_trip() -> None:
    kanji = make_kanji()
    dumped = kanji.model_dump()
    assert PracticeKanji.model_validate(dumped) == kanji


def test_deactivate_and_activate_touch() -> None:
    item = make_kanji()
    item.deactivate()
    assert item.is_active is False
    assert item.updated_at > NOW

    touched = item.updated_at
    item.activate()
    assert item.is_active is True
    assert item.updated_at >= touched


def test_activate_when_active_does_not_touch() -> None:
    item = make_kanji()
    item.activate()

    assert item.updated_at == NOW
