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
    LastMeaningError,
    LastReadingError,
    OriginalDataError,
    SenseLanguageError,
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
                        text="to scoff (colloquial)",
                        lang="eng",
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
        ("senses", lambda e: e.senses[0]),
        ("glosses", lambda e: e.senses[0].glosses[0]),
        ("examples", lambda e: e.senses[0].examples[0]),
    ],
)
def test_set_enabled_toggles_one_item(
    part: EntryPart,
    get: Callable[
        [PracticeEntry],
        PracticeKanjiReading
        | PracticeReading
        | PracticeSense
        | PracticeGloss
        | PracticeExample,
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

    entry.edit_gloss(2, "to wolf down")
    assert entry.senses[0].glosses[1].text == "to wolf down"
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


def test_disabling_a_sense_keeps_its_meanings_flags() -> None:
    entry = stored_entry()
    entry.set_enabled("glosses", 2, False)

    entry.set_enabled("senses", 1, False)
    entry.set_enabled("senses", 1, True)

    assert [g.enabled for g in entry.senses[0].glosses] == [True, False]


def test_add_and_remove_own_senses() -> None:
    entry = stored_entry()

    sense = entry.add_sense("  to dine  ", "eng")

    assert entry.senses[-1] is sense
    assert (sense.id, sense.origin, sense.enabled) == (None, "added", True)
    assert [(g.text, g.origin) for g in sense.glosses] == [("to dine", "added")]
    assert entry.updated_at > NOW
    sense.id = 2  # as stored
    entry.remove_sense(2)
    assert [s.id for s in entry.senses] == [1]


def test_own_senses_start_with_a_meaning() -> None:
    with pytest.raises(ValueError):
        stored_entry().add_sense("   ", "eng")


def test_dictionary_senses_can_be_disabled_but_not_removed() -> None:
    entry = stored_entry()
    with pytest.raises(OriginalDataError):
        entry.remove_sense(1)
    with pytest.raises(EntityNotFoundError):
        entry.remove_sense(99)
    assert len(entry.senses) == 1


def _texts(example: PracticeExample) -> list[tuple[str, str]]:
    return [(s.lang, s.text) for s in example.sentences]


def test_add_edit_and_remove_own_examples() -> None:
    entry = stored_entry()

    added = entry.add_example(1, " 朝ご飯を食べる。 ", " I eat breakfast. ", "eng")
    assert (added.id, added.origin, added.text) == (None, "added", "")
    assert entry.senses[0].examples[-1] is added
    assert _texts(added) == [("jpn", "朝ご飯を食べる。"), ("eng", "I eat breakfast.")]
    assert entry.updated_at > NOW

    added.id = 2  # as stored
    entry.edit_example(2, "朝ご飯を食べた。", "Desayuné.", "spa")
    assert _texts(added) == [
        ("jpn", "朝ご飯を食べた。"),
        ("spa", "Desayuné."),
        ("eng", "I eat breakfast."),
    ]
    entry.edit_example(2, "朝ご飯を食べた。", "  ", "eng")
    assert _texts(added) == [("jpn", "朝ご飯を食べた。"), ("spa", "Desayuné.")]

    entry.remove_example(2)
    assert [e.id for e in entry.senses[0].examples] == [1]


def test_own_examples_without_a_translation_or_change() -> None:
    entry = stored_entry()
    added = entry.add_example(1, "食べる。", None, "eng")
    assert _texts(added) == [("jpn", "食べる。")]

    added.id = 2
    touched = entry.updated_at
    entry.edit_example(2, "食べる。", None, "eng")
    assert entry.updated_at == touched


def test_own_examples_need_a_sentence_and_a_foreign_translation() -> None:
    entry = stored_entry()
    with pytest.raises(ValueError):
        entry.add_example(1, "   ", "x", "eng")
    with pytest.raises(ValueError):
        entry.add_example(1, "食べる。", "食べる。", "jpn")
    with pytest.raises(EntityNotFoundError):
        entry.add_example(99, "食べる。", None, "eng")


def test_dictionary_examples_can_be_disabled_but_not_changed() -> None:
    entry = stored_entry()
    with pytest.raises(OriginalDataError):
        entry.edit_example(1, "x", None, "eng")
    with pytest.raises(OriginalDataError):
        entry.remove_example(1)
    with pytest.raises(EntityNotFoundError):
        entry.remove_example(99)


def test_create_own_word() -> None:
    entry = PracticeEntry.create_own(
        USER_ID,
        [" 三匹 ", "三匹"],
        ["さんびき", " サンビキ "],
        " three animals ",
        "eng",
    )

    assert entry.is_own and entry.source_entry_id is None and entry.id is None
    assert [(k.kanji, k.origin) for k in entry.kanji_readings] == [("三匹", "added")]
    assert [(r.text, r.origin) for r in entry.readings] == [
        ("さんびき", "added"),
        ("サンビキ", "added"),
    ]
    (sense,) = entry.senses
    assert sense.origin == "added"
    assert [(g.text, g.lang, g.origin) for g in sense.glosses] == [
        ("three animals", "eng", "added")
    ]
    assert (entry.jlpt, entry.is_common, entry.is_active) == (None, False, True)


def test_imported_words_are_not_own() -> None:
    assert make_entry().is_own is False


def test_own_word_needs_a_kana_reading_and_a_meaning() -> None:
    with pytest.raises(ValueError):
        PracticeEntry.create_own(USER_ID, ["三匹"], [], "three animals", "eng")
    with pytest.raises(ValueError):
        PracticeEntry.create_own(USER_ID, ["三匹"], ["sanbiki"], "x", "eng")
    with pytest.raises(ValueError):
        PracticeEntry.create_own(USER_ID, [], ["さんびき"], "  ", "eng")
    with pytest.raises(ValueError):
        PracticeEntry.create_own(USER_ID, [" "], ["さんびき"], "x", "eng")


def test_add_and_remove_own_spellings_and_readings() -> None:
    entry = stored_entry()

    spelling = entry.add_spelling(" 喰べる ")
    reading = entry.add_reading("クウ")
    assert (spelling.kanji, spelling.origin) == ("喰べる", "added")
    assert (reading.text, reading.origin) == ("クウ", "added")
    assert entry.updated_at > NOW

    spelling.id, reading.id = 2, 3  # as stored
    entry.remove_spelling(2)
    entry.remove_reading(3)
    assert [k.id for k in entry.kanji_readings] == [1]
    assert [r.text for r in entry.readings] == ["たべる"]
    with pytest.raises(ValueError):
        entry.add_reading("taberu")


def test_dictionary_spellings_and_readings_are_only_disabled() -> None:
    entry = stored_entry()
    with pytest.raises(OriginalDataError):
        entry.remove_spelling(1)
    with pytest.raises(OriginalDataError):
        entry.remove_reading(1)
    with pytest.raises(EntityNotFoundError):
        entry.remove_reading(99)


def test_a_word_keeps_its_last_reading() -> None:
    entry = PracticeEntry.create_own(USER_ID, [], ["ねこ"], "cat", "eng")
    entry.readings[0].id = 1

    with pytest.raises(LastReadingError):
        entry.remove_reading(1)
    assert len(entry.readings) == 1


def test_a_sense_keeps_its_last_meaning() -> None:
    entry = stored_entry()
    sense = entry.add_sense("to dine", "eng")
    sense.id, sense.glosses[0].id = 2, 3  # as stored
    entry.add_gloss(2, "to sup", "eng").id = 4

    entry.remove_gloss(4)
    with pytest.raises(LastMeaningError):
        entry.remove_gloss(3)
    assert [g.text for g in entry.senses[-1].glosses] == ["to dine"]
    entry.remove_sense(2)  # the way to get rid of it
    assert [s.id for s in entry.senses] == [1]


def test_a_senses_meanings_are_in_one_language() -> None:
    entry = stored_entry()
    with pytest.raises(SenseLanguageError):
        entry.add_gloss(1, "comer", "spa")
    assert [g.lang for g in entry.senses[0].glosses] == ["eng", "eng"]
