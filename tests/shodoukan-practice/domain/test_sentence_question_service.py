from random import Random
from uuid import uuid4

import pytest
from pydantic import ValidationError

from shodoukan_practice.domain.entities import (
    Direction,
    EntryExercise,
    ExerciseQuestion,
    Inflection,
    KanjiExercise,
    SentenceChoiceQuestion,
    SentenceChoiceSettings,
)
from shodoukan_practice.domain.exceptions import ExercisePoolTooSmallError
from shodoukan_practice.domain.repositories import GapText
from shodoukan_practice.domain.services import (
    FieldValue,
    StudyCard,
    build_next_sentence_question,
    gloss_key,
    kana_key,
)

PAST = Inflection(endings=("た",), form="終止形")
NOUN = Inflection(endings=(), form=None)

FILL = Direction(prompt=("meaning",), answer="writing")
READ = Direction(prompt=("writing",), answer="reading")
MEAN = Direction(prompt=("writing",), answer="meaning")


def settings(*directions: Direction, **extra: object) -> SentenceChoiceSettings:
    return SentenceChoiceSettings.model_validate(
        {"directions": [d.model_dump() for d in directions], **extra}
    )


def word(item_id: int, writing: str, reading: str, meaning: str) -> StudyCard:
    return StudyCard(
        item_id,
        {
            "writing": (FieldValue(writing, frozenset({writing})),),
            "reading": (FieldValue(reading, frozenset({kana_key(reading)})),),
            "meaning": (FieldValue(meaning, frozenset({gloss_key(meaning)})),),
        },
        first_only=frozenset({"writing", "reading"}),
    )


def gap(
    sentence_id: int,
    text: str,
    surface: str,
    reading: str,
    inflection: Inflection = PAST,
    pos: str = "動詞",
    translation: str | None = None,
) -> GapText:
    start = text.index(surface)
    return GapText(
        entry_id=sentence_id // 10,
        sentence_id=sentence_id,
        sentence=text,
        start=start,
        end=start + len(surface),
        reading=reading,
        pos=pos,
        inflection=inflection,
        translation=translation,
    )


EAT = word(1, "食べる", "たべる", "to eat")
DRINK = word(2, "飲む", "のむ", "to drink")
READ_BOOK = word(3, "読む", "よむ", "to read")
WATER = word(4, "水", "みず", "water")
CARDS = [EAT, DRINK, READ_BOOK, WATER]
ATE = "パンを食べた。"
GAPS = {
    1: [gap(10, ATE, "食べた", "たべた", translation="I ate bread.")],
    2: [gap(20, "水を飲んだ。", "飲んだ", "のんだ")],
    3: [gap(30, "本を読んだ。", "読んだ", "よんだ")],
    # A noun: never an option for a verb in the past.
    4: [gap(40, "水が冷たい。", "水", "みず", NOUN, pos="名詞")],
}
VERBS_PAST = {"食べた", "飲んだ", "読んだ"}


def ask(
    direction: Direction,
    cards: list[StudyCard] = CARDS,
    seed: int = 1,
    history: list[ExerciseQuestion] | None = None,
    **extra: object,
) -> SentenceChoiceQuestion:
    return build_next_sentence_question(
        cards, GAPS, settings(direction, **extra), history or [], Random(seed)
    )


def test_settings_ask_a_words_writing_reading_or_meaning() -> None:
    assert settings(FILL, READ, MEAN).type == "sentence.choice"
    with pytest.raises(ValidationError):
        settings(Direction(prompt=("meaning",), answer="reading"))  # word not shown
    with pytest.raises(ValidationError):
        settings(Direction(prompt=("reading",), answer="literal"))


def test_sentence_exercises_are_for_words() -> None:
    assert EntryExercise(id=None, user_id=uuid4(), name="x", settings=settings(FILL))
    with pytest.raises(ValidationError):
        KanjiExercise(id=None, user_id=uuid4(), name="x", settings=settings(FILL))


def test_fill_the_gap_offers_words_in_the_same_form() -> None:
    question = ask(FILL)

    answer = question.options[question.correct_option]
    shown = GAPS[question.item_id or 0][0]
    assert question.answer_field == "writing"
    assert answer.text == shown.surface
    assert question.sentence == shown.sentence
    assert (question.gap_start, question.gap_end) == (shown.start, shown.end)
    # Verbs in the past only: 水 (a noun) is never one of them.
    assert {o.text for o in question.options} == VERBS_PAST


def test_a_word_alone_in_its_form_isnt_asked_to_fill() -> None:
    for seed in range(10):
        assert ask(FILL, seed=seed).item_id != 4
    # 水 and one verb: neither has a gap in the same form as another.
    with pytest.raises(ExercisePoolTooSmallError):
        ask(FILL, cards=[WATER, DRINK])


def test_the_reading_in_context_with_its_translation() -> None:
    for seed in range(6):
        question = ask(READ, [EAT, DRINK, READ_BOOK], seed, show_translation=True)

        answer = question.options[question.correct_option]
        assert answer.text == GAPS[question.item_id or 0][0].reading
        assert {o.text for o in question.options} == {"たべた", "のんだ", "よんだ"}
        if question.item_id == 1:
            assert question.translation == "I ate bread."
    assert ask(READ, [EAT, DRINK]).translation is None  # not asked for


def test_the_meaning() -> None:
    question = ask(MEAN)

    answer = question.options[question.correct_option]
    assert answer.item_id == question.item_id
    meanings = {"to eat", "to drink", "to read", "water"}
    assert {o.text for o in question.options} <= meanings


def test_a_word_rotates_through_its_sentences() -> None:
    more = {**GAPS, 1: [*GAPS[1], gap(11, "肉を食べた。", "食べた", "たべた")]}
    history: list[ExerciseQuestion] = []
    for _ in range(12):
        question = build_next_sentence_question(
            CARDS, more, settings(MEAN), history, Random(len(history))
        )
        question.is_correct = True
        history.append(question)

    asked = [
        q.sentence_id
        for q in history
        if isinstance(q, SentenceChoiceQuestion) and q.item_id == 1
    ]
    assert set(asked) == {10, 11}
    assert abs(asked.count(10) - asked.count(11)) <= 1


def test_a_pool_needs_words_with_sentences() -> None:
    with pytest.raises(ExercisePoolTooSmallError):
        build_next_sentence_question(CARDS, {1: GAPS[1]}, settings(FILL), [], Random(1))
