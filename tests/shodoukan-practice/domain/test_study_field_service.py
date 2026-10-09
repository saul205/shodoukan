from typing import TypeVar

from factories import USER_ID, make_entry, make_kanji, make_word

from shodoukan_practice.domain.entities import (
    ENTRY_FIELDS,
    KANJI_FIELDS,
    PracticeEntry,
    PracticeKanji,
    StudyField,
)
from shodoukan_practice.domain.services import (
    entry_card,
    entry_label,
    gloss_key,
    kana_key,
    kanji_card,
)


def test_kana_key() -> None:
    assert kana_key("ショク") == "しょく"
    assert kana_key("た.べる") == "たべる"
    assert kana_key("-た") == "た"
    assert kana_key("たべる") == "たべる"


def test_gloss_key() -> None:
    assert gloss_key("To Eat") == "eat"
    assert gloss_key("to eat (food)") == "eat"
    assert gloss_key("  bridge  ") == "bridge"
    assert gloss_key("(something) to eat") == "eat"


T = TypeVar("T", PracticeEntry, PracticeKanji)


def _stored(item: T, item_id: int) -> T:
    """As if loaded from the library: with an id."""
    return item.model_copy(update={"id": item_id})


def test_entry_card_reads_enabled_parts() -> None:
    entry = _stored(make_entry(USER_ID), 7)
    entry.readings[1].enabled = False  # くう hidden

    card = entry_card(entry, ENTRY_FIELDS, "eng")

    assert card.item_id == 7
    assert [v.text for v in card.get("writing")] == ["食べる"]
    assert [v.text for v in card.get("reading")] == ["たべる"]
    assert [v.text for v in card.get("meaning")] == ["to eat"]
    assert card.keys("meaning") == {"eat"}


def test_entry_meaning_is_the_first_sense_in_the_language() -> None:
    entry = _stored(make_word(USER_ID, 1, "橋", "はし", [("puente", "spa")]), 1)
    assert entry_card(entry, ENTRY_FIELDS, "eng").get("meaning") == ()
    assert [v.text for v in entry_card(entry, ENTRY_FIELDS, "spa").get("meaning")] == [
        "puente"
    ]


def test_entry_meaning_skips_disabled_senses() -> None:
    entry = _stored(make_entry(USER_ID), 7)
    entry.add_sense("to dine", "eng")
    entry.senses[0].enabled = False

    assert [v.text for v in entry_card(entry, ENTRY_FIELDS, "eng").get("meaning")] == [
        "to dine"
    ]


def test_entry_meaning_joins_glosses_and_keys_each() -> None:
    entry = _stored(
        make_word(
            USER_ID, 1, "話す", "はなす", [("to speak", "eng"), ("to talk", "eng")]
        ),
        1,
    )
    (meaning,) = entry_card(entry, ENTRY_FIELDS, "eng").get("meaning")
    assert meaning.text == "to speak; to talk"
    assert meaning.keys == {"speak", "talk"}


def test_only_the_first_spelling_and_reading_of_a_word_are_asked() -> None:
    entry = _stored(make_entry(USER_ID), 7)  # たべる, then くう
    card = entry_card(entry, ENTRY_FIELDS, "eng")

    assert [v.text for v in card.get("reading")] == ["たべる", "くう"]
    assert [v.text for v in card.answers("reading")] == ["たべる"]
    assert card.keys("reading") == {"たべる", "くう"}  # still compared

    entry.readings[0].enabled = False
    card = entry_card(entry, ENTRY_FIELDS, "eng")
    assert [v.text for v in card.answers("reading")] == ["くう"]


def test_every_kanji_reading_can_be_asked() -> None:
    card = kanji_card(_stored(make_kanji(USER_ID), 3), KANJI_FIELDS, "en")
    assert [v.text for v in card.answers("kunyomi")] == ["た.べる", "く.う"]


def test_kana_only_word_has_no_writing() -> None:
    entry = _stored(make_word(USER_ID, 1, None, "これ", [("this", "eng")]), 1)
    card = entry_card(entry, ENTRY_FIELDS, "eng")
    assert not card.has("writing")
    assert card.has("reading", "meaning")


def test_only_requested_fields_are_read() -> None:
    card = entry_card(
        _stored(make_entry(USER_ID), 1), frozenset[StudyField]({"reading"}), "eng"
    )
    assert set(card.values) == {"reading"}


def test_kanji_card() -> None:
    kanji = _stored(make_kanji(USER_ID), 3)
    kanji.meanings[1].enabled = False  # "food" hidden

    card = kanji_card(kanji, KANJI_FIELDS, "en")

    assert [v.text for v in card.get("literal")] == ["食"]
    assert [v.text for v in card.get("onyomi")] == ["ショク"]
    assert card.keys("onyomi") == {"しょく"}
    assert [v.text for v in card.get("kunyomi")] == ["た.べる", "く.う"]
    assert card.keys("kunyomi") == {"たべる", "くう"}
    assert [v.text for v in card.get("meaning")] == ["eat"]


def _stored_word(spelling: str | None, reading: str) -> PracticeEntry:
    word = make_word(USER_ID, 1, spelling, reading, [("to eat", "eng")])
    return word.model_copy(update={"id": 1})


def test_entry_label_is_the_usual_form_and_its_reading() -> None:
    assert entry_label(_stored_word("食べる", "たべる")) == ("食べる", "たべる")
    assert entry_label(_stored_word(None, "すし")) == ("すし", None)


def test_entry_label_follows_what_the_user_disabled() -> None:
    word = _stored_word("食べる", "たべる")
    word.kanji_readings[0].enabled = False
    assert entry_label(word) == ("たべる", None)
    word.readings[0].enabled = False
    assert entry_label(word) == ("食べる", None)  # all hidden: the dictionary's
