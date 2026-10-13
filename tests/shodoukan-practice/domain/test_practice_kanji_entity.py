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


# --- Sharing ---


def origin_kanji() -> PracticeKanji:
    kanji = make_kanji()
    kanji.meanings[1].id = 2
    kanji.kun_readings[0].enabled = False
    kanji.notes = "the owner's note"
    kanji.is_active = False
    return kanji


def fresh_snapshot() -> PracticeKanji:
    kanji = make_kanji()
    kanji.meanings.pop()
    return kanji.model_copy(update={"id": None})


def test_kanji_to_shared() -> None:
    shared = origin_kanji().to_shared()
    assert shared.literal == "食"
    assert [(r.text, r.enabled) for r in shared.kun_readings] == [("た.べる", False)]
    assert [(m.origin, m.id) for m in shared.meanings] == [
        ("imported", 1),
        ("added", 2),
    ]


def test_kanji_merge_into_a_created_copy_takes_everything() -> None:
    kanji = fresh_snapshot()
    kanji.merge_shared(origin_kanji().to_shared(), created=True)
    assert kanji.is_active is False
    assert kanji.notes == "the owner's note"
    assert kanji.kun_readings[0].enabled is False
    assert [(m.text, m.source_id) for m in kanji.meanings] == [
        ("eat", None),
        ("food (extra)", 2),
    ]
    assert kanji.updated_at > NOW


def test_kanji_merge_into_an_existing_one_keeps_the_users_choices() -> None:
    kanji = fresh_snapshot()
    kanji.notes = "mine"
    kanji.merge_shared(origin_kanji().to_shared(), created=False)
    assert kanji.is_active is True
    assert kanji.notes == "mine"
    assert kanji.kun_readings[0].enabled is True
    assert [m.text for m in kanji.meanings] == ["eat", "food (extra)"]

    before = kanji.model_copy(deep=True)
    kanji.merge_shared(origin_kanji().to_shared(), created=False)
    assert kanji == before


def test_kanji_merge_refuses_another_character() -> None:
    other = origin_kanji().to_shared().model_copy(update={"literal": "飲"})
    with pytest.raises(ValueError, match="飲"):
        make_kanji().merge_shared(other, created=False)


def test_kanji_sharing_notes_and_attribution() -> None:
    assert origin_kanji().to_shared(include_notes=False).notes is None
    kanji = fresh_snapshot()
    kanji.merge_shared(origin_kanji().to_shared(), created=True, source_collection_id=4)
    assert [m.source_collection_id for m in kanji.meanings] == [None, 4]


def test_kanji_prune_and_dismissed_meanings() -> None:
    origin = origin_kanji()
    copy = fresh_snapshot()
    copy.merge_shared(origin.to_shared(), created=True, source_collection_id=3)
    copy.meanings[1].id = 50
    origin.meanings.pop()

    assert copy.prune_source(origin.to_shared(), 3) is True
    assert [m.text for m in copy.meanings] == ["eat"]
    assert copy.shared_key == origin.to_shared().key == "kanji:食"

    again = fresh_snapshot()
    again.merge_shared(origin_kanji().to_shared(), created=True)
    again.meanings[1].id = 60
    again.remove_meaning(60)
    again.merge_shared(origin_kanji().to_shared(), created=False)
    assert [m.text for m in again.meanings] == ["eat"]
