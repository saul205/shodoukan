from datetime import UTC, datetime
from uuid import UUID

import pytest

from shodoukan_practice.domain.entities import (
    PracticeKanji,
    PracticeKanjiMeaning,
    PracticeReadingItem,
)
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    OriginalDataError,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a001")


def make_kanji() -> PracticeKanji:
    return PracticeKanji(
        id=1,
        user_id=USER_ID,
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


def stored_kanji() -> PracticeKanji:
    kanji = make_kanji()
    kanji.meanings[1].id = 2
    return kanji


def test_kanji_set_notes() -> None:
    kanji = stored_kanji()
    kanji.set_notes(" radical: 食 ")
    assert kanji.notes == "radical: 食"
    assert kanji.updated_at > NOW


def test_set_enabled_covers_every_reading_kind_and_meanings() -> None:
    kanji = stored_kanji()

    kanji.set_enabled("readings", 2, False)  # a kun reading
    kanji.set_enabled("meanings", 1, False)

    assert kanji.kun_readings[0].enabled is False
    assert kanji.on_readings[0].enabled is True
    assert kanji.meanings[0].enabled is False
    with pytest.raises(EntityNotFoundError):
        kanji.set_enabled("readings", 99, False)


def test_original_kanji_meanings_cant_be_changed() -> None:
    kanji = stored_kanji()
    with pytest.raises(OriginalDataError):
        kanji.edit_meaning(1, "to eat")
    with pytest.raises(OriginalDataError):
        kanji.remove_meaning(1)


def test_add_edit_and_remove_own_kanji_meanings() -> None:
    kanji = stored_kanji()

    added = kanji.add_meaning("meal", "en")
    kanji.edit_meaning(2, "food")
    kanji.remove_meaning(2)

    assert added.origin == "added"
    assert [m.text for m in kanji.meanings] == ["eat", "meal"]
    assert kanji.updated_at > NOW
