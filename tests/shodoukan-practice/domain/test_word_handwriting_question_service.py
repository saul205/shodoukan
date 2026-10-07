from random import Random

import pytest
from factories import make_reference, word_handwriting_settings

from shodoukan_practice.domain.entities import (
    MAX_CELLS,
    HandwritingCardSettings,
    StudyField,
)
from shodoukan_practice.domain.exceptions import ExercisePoolTooSmallError
from shodoukan_practice.domain.services import (
    FieldValue,
    StudyCard,
    WordHandwritingDraft,
    draft_next_word_question,
    ensure_enough_writable_items,
    kana_key,
    word_characters,
)


def _word(item_id: int, writing: str | None, reading: str, meaning: str) -> StudyCard:
    values: dict[StudyField, tuple[FieldValue, ...]] = {
        "reading": (FieldValue(reading, frozenset({kana_key(reading)})),),
        "meaning": (FieldValue(meaning, frozenset({meaning})),),
    }
    if writing is not None:
        values["writing"] = (FieldValue(writing, frozenset({writing})),)
    return StudyCard(item_id, values, first_only=frozenset({"writing", "reading"}))


POOL = [
    _word(1, "橋", "はし", "bridge"),
    _word(2, "箸", "はし", "chopsticks"),
    _word(3, "食べる", "たべる", "to eat"),
    _word(4, None, "これ", "this"),
    _word(5, "見る", "みる", "to see"),
]
DRAWABLE = frozenset("橋箸食べるたこれはし")
WRITING = word_handwriting_settings((("reading",), "writing"))
READING = word_handwriting_settings((("meaning",), "reading"))


def _drafts(
    settings: HandwritingCardSettings,
    pool: list[StudyCard] = POOL,
    drawable: frozenset[str] = DRAWABLE,
) -> dict[int, WordHandwritingDraft]:
    return {
        d.item_id: d
        for d in (
            draft_next_word_question(pool, settings, [], drawable, Random(seed))
            for seed in range(30)
        )
    }


def test_every_word_that_fits_the_prompt_and_is_as_long_is_accepted() -> None:
    drafts = _drafts(WRITING)

    assert drafts[1].accepted == ("橋", "箸")
    assert drafts[3].accepted == ("食べる",)
    assert drafts[3].characters == frozenset("食べる")
    # これ has no writing; 見 has no stroke order.
    assert set(drafts) == {1, 2, 3}


def test_the_reading_is_written_in_kana() -> None:
    drafts = _drafts(READING)

    assert drafts[3].accepted == ("たべる",)
    assert drafts[4].accepted == ("これ",)
    assert 5 not in drafts  # み has no stroke order


def test_a_word_longer_than_the_cells_isnt_asked() -> None:
    long = "は" * (MAX_CELLS + 1)
    pool = [_word(1, None, long, "long"), _word(2, None, "はし", "x")]

    with pytest.raises(ExercisePoolTooSmallError):
        ensure_enough_writable_items(pool, READING, DRAWABLE)


def test_word_characters_lists_what_could_be_asked() -> None:
    assert word_characters(POOL[2:4], WRITING) == set("食べる")
    assert word_characters(POOL[2:4], READING) == set("たべるこれ")


def test_the_draft_becomes_the_question() -> None:
    draft = _drafts(WRITING)[3]

    question = draft.question(2, {c: make_reference(c) for c in "食べる"})

    assert (question.position, question.item_id) == (2, 3)
    assert (question.answer_field, question.cell_count) == ("writing", 3)
    assert question.words[0].text == "食べる"


def test_the_asked_word_needs_every_stroke_order() -> None:
    draft = _drafts(WRITING)[3]

    with pytest.raises(ExercisePoolTooSmallError):
        draft.question(0, {c: make_reference(c) for c in "食べ"})
