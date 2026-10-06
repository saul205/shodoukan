from random import Random

import pytest
from factories import handwriting_settings, make_reference

from shodoukan_practice.domain.exceptions import ExercisePoolTooSmallError
from shodoukan_practice.domain.services import (
    FieldValue,
    StudyCard,
    draft_next_question,
    ensure_enough_drawable_items,
    kana_key,
)


def _kanji(item_id: int, literal: str, kun: str, meaning: str) -> StudyCard:
    return StudyCard(
        item_id=item_id,
        values={
            "literal": (FieldValue(literal, frozenset({literal})),),
            "kunyomi": (FieldValue(kun, frozenset({kana_key(kun)})),),
            "meaning": (FieldValue(meaning, frozenset({meaning})),),
        },
    )


POOL = [
    _kanji(1, "橋", "はし", "bridge"),
    _kanji(2, "箸", "はし", "chopsticks"),
    _kanji(3, "水", "みず", "water"),
    _kanji(4, "木", "き", "tree"),
]
DRAWABLE = frozenset({"橋", "箸", "水"})


def test_every_kanji_that_fits_the_prompt_is_accepted() -> None:
    settings = handwriting_settings(("kunyomi",))
    drafts = [
        draft_next_question(POOL, settings, [], DRAWABLE, Random(seed))
        for seed in range(20)
    ]

    accepted = {d.item_id: d.accepted for d in drafts}
    assert accepted[1] == ("橋", "箸")
    assert accepted[2] == ("箸", "橋")
    assert accepted[3] == ("水",)
    assert 4 not in accepted  # 木 has no stroke order


def test_the_draft_becomes_the_question() -> None:
    draft = draft_next_question(
        POOL, handwriting_settings(("meaning",)), [], DRAWABLE, Random(1)
    )

    question = draft.question(3, [make_reference(draft.accepted[0])])

    assert question.position == 3
    assert question.item_id == draft.item_id
    assert (question.prompt_fields, question.answer_field) == (("meaning",), "literal")
    assert question.references[0].literal == draft.accepted[0]
    assert question.back[-1].field == "literal"


def test_a_pool_needs_two_kanji_with_a_stroke_order() -> None:
    settings = handwriting_settings(("meaning",))

    with pytest.raises(ExercisePoolTooSmallError):
        ensure_enough_drawable_items(POOL, settings, frozenset({"水"}))
    with pytest.raises(ExercisePoolTooSmallError):
        draft_next_question(POOL, settings, [], frozenset({"水"}), Random(1))
