from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from shodoukan_practice.domain.entities import (
    EntryPart,
    PracticeEntry,
    PracticeExample,
    PracticeExampleSentence,
    PracticeGloss,
    PracticeKanjiReading,
    PracticeReading,
    PracticeSense,
)
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    OriginalDataError,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a001")


def make_entry() -> PracticeEntry:
    return PracticeEntry(
        id=1,
        user_id=USER_ID,
        source_entry_id=1000001,
        kanji_readings=[
            PracticeKanjiReading(id=1, kanji="食べる", info=[]),
        ],
        readings=[
            PracticeReading(
                id=1,
                text="たべる",
                no_kanji=False,
                info=[],
                restricted_to=[],
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
                        id=None,
                        text="jamar (coloquial)",
                        lang="spa",
                        type=None,
                        origin="added",
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


def test_practice_entry_shape_and_defaults() -> None:
    entry = make_entry()
    assert entry.is_active is True
    assert entry.senses[0].glosses[0].enabled is True
    assert entry.senses[0].glosses[0].origin == "imported"
    assert entry.senses[0].glosses[1].origin == "added"


def test_practice_entry_serializes_round_trip() -> None:
    entry = make_entry()
    dumped = entry.model_dump()
    assert PracticeEntry.model_validate(dumped) == entry


def test_deactivate_and_activate_touch() -> None:
    item = make_entry()
    item.deactivate()
    assert item.is_active is False
    assert item.updated_at > NOW

    touched = item.updated_at
    item.activate()
    assert item.is_active is True
    assert item.updated_at >= touched


def test_activate_when_active_does_not_touch() -> None:
    item = make_entry()
    item.activate()

    assert item.updated_at == NOW


def stored_entry() -> PracticeEntry:
    """`make_entry` as loaded from the database: every nested item has an id."""
    entry = make_entry()
    entry.senses[0].glosses[1].id = 2
    return entry


def test_set_notes_cleans_and_touches_only_on_change() -> None:
    entry = stored_entry()

    entry.set_notes("  ichidan  ")
    assert entry.notes == "ichidan"
    assert entry.updated_at > NOW

    touched = entry.updated_at
    entry.set_notes("ichidan")
    assert entry.updated_at == touched
    entry.set_notes("   ")
    assert entry.notes is None


def test_set_sense_notes() -> None:
    entry = stored_entry()

    entry.set_sense_notes(1, "polite: 召し上がる")

    assert entry.senses[0].notes == "polite: 召し上がる"
    assert entry.updated_at > NOW
    with pytest.raises(EntityNotFoundError):
        entry.set_sense_notes(99, "x")
    with pytest.raises(ValidationError):
        entry.set_sense_notes(1, "x" * 2001)


@pytest.mark.parametrize(
    ("part", "get"),
    [
        ("kanji_readings", lambda e: e.kanji_readings[0]),
        ("readings", lambda e: e.readings[0]),
        ("glosses", lambda e: e.senses[0].glosses[0]),
        ("examples", lambda e: e.senses[0].examples[0]),
    ],
)
def test_set_enabled_toggles_one_item(
    part: EntryPart,
    get: Callable[
        [PracticeEntry],
        PracticeKanjiReading | PracticeReading | PracticeGloss | PracticeExample,
    ],
) -> None:
    entry = stored_entry()

    entry.set_enabled(part, 1, False)

    assert get(entry).enabled is False
    assert entry.updated_at > NOW


def test_set_enabled_without_change_does_not_touch() -> None:
    entry = stored_entry()
    entry.set_enabled("readings", 1, True)
    assert entry.updated_at == NOW


def test_set_enabled_of_an_unknown_item_fails() -> None:
    with pytest.raises(EntityNotFoundError):
        stored_entry().set_enabled("glosses", 99, False)


def test_original_meanings_can_be_disabled_but_not_changed() -> None:
    entry = stored_entry()

    entry.set_enabled("glosses", 1, False)  # the dictionary's "to eat"

    with pytest.raises(OriginalDataError):
        entry.edit_gloss(1, "to devour")
    with pytest.raises(OriginalDataError):
        entry.remove_gloss(1)
    assert entry.senses[0].glosses[0].text == "to eat"


def test_add_edit_and_remove_own_meanings() -> None:
    entry = stored_entry()

    added = entry.add_gloss(1, "  to scoff  ", "eng")
    assert (added.text, added.origin, added.id) == ("to scoff", "added", None)
    assert entry.senses[0].glosses[-1] is added

    entry.edit_gloss(2, "jamar")
    assert entry.senses[0].glosses[1].text == "jamar"
    entry.remove_gloss(2)
    assert [g.text for g in entry.senses[0].glosses] == ["to eat", "to scoff"]
    assert entry.updated_at > NOW


def test_own_meanings_cant_be_empty() -> None:
    entry = stored_entry()
    with pytest.raises(ValueError):
        entry.add_gloss(1, "   ", "eng")
    with pytest.raises(ValueError):
        entry.edit_gloss(2, "")
    with pytest.raises(EntityNotFoundError):
        entry.add_gloss(99, "x", "eng")
