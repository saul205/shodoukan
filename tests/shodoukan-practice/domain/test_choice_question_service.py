from itertools import pairwise
from random import Random

import pytest
from factories import choice_settings

from shodoukan_practice.domain.entities import (
    ChoiceCardSettings,
    ChoiceQuestion,
    OptionAnswer,
)
from shodoukan_practice.domain.exceptions import ExercisePoolTooSmallError
from shodoukan_practice.domain.services import (
    REVIEW_GAP,
    FieldValue,
    StudyCard,
    build_next_question,
    gloss_key,
    kana_key,
)


def _kana(*texts: str) -> tuple[FieldValue, ...]:
    return tuple(FieldValue(t, frozenset({kana_key(t)})) for t in texts)


def _as_is(*texts: str) -> tuple[FieldValue, ...]:
    return tuple(FieldValue(t, frozenset({t})) for t in texts)


def _meaning(*glosses: str) -> tuple[FieldValue, ...]:
    return (FieldValue("; ".join(glosses), frozenset(map(gloss_key, glosses))),)


def kanji(
    item_id: int, literal: str, on: str = "", kun: str = "", meaning: str = ""
) -> StudyCard:
    return StudyCard(
        item_id,
        {
            "literal": _as_is(literal),
            "onyomi": _kana(*on.split()),
            "kunyomi": _kana(*kun.split()),
            "meaning": _meaning(meaning) if meaning else (),
        },
    )


def word(item_id: int, writing: str | None, reading: str, *glosses: str) -> StudyCard:
    return StudyCard(
        item_id,
        {
            "writing": _as_is(writing) if writing else (),
            "reading": _kana(*reading.split()),
            "meaning": _meaning(*glosses),
        },
        first_only=frozenset({"writing", "reading"}),
    )


def _texts(question: ChoiceQuestion) -> list[str]:
    return [option.text for option in question.options]


def _play(
    cards: list[StudyCard],
    settings: ChoiceCardSettings,
    rng: Random,
    count: int,
    wrong: frozenset[int] = frozenset(),
) -> list[ChoiceQuestion]:
    """A session of `count` questions, answering right except for `wrong` items."""
    history: list[ChoiceQuestion] = []
    for _ in range(count):
        question = build_next_question(cards, settings, history, rng)
        option = question.correct_option
        if question.item_id in wrong:
            option = (option + 1) % len(question.options)
        history.append(
            question.model_copy(
                update={
                    "answer": OptionAnswer(option=option),
                    "is_correct": option == question.correct_option,
                }
            )
        )
    return history


def _build(
    cards: list[StudyCard], settings: ChoiceCardSettings, seeds: range = range(30)
) -> list[ChoiceQuestion]:
    """Questions from many sessions, so a rule must hold whatever the dice say."""
    return [q for seed in seeds for q in _play(cards, settings, Random(seed), 8)]


FILLER = [
    kanji(10, "水", on="スイ", kun="みず", meaning="water"),
    kanji(11, "火", on="カ", kun="ひ", meaning="fire"),
    kanji(12, "木", on="モク", kun="き", meaning="tree"),
    kanji(13, "山", on="サン", kun="やま", meaning="mountain"),
]


def test_question_shape() -> None:
    settings = choice_settings((("literal",), "kunyomi"), back_fields=["meaning"])
    cards = [kanji(1, "食", on="ショク", kun="た.べる く.う", meaning="eat"), *FILLER]

    questions = _play(cards, settings, Random(1), 5)

    assert [q.position for q in questions] == [0, 1, 2, 3, 4]
    question = next(q for q in questions if q.item_id == 1)
    assert question.id is None
    assert question.prompt_fields == ("literal",)
    assert question.answer_field == "kunyomi"
    assert [(f.field, f.values) for f in question.prompt] == [("literal", ("食",))]
    assert len(question.options) == 4
    correct = question.options[question.correct_option]
    assert correct.item_id == 1
    assert correct.text in ("た.べる", "く.う")
    # The back shows the prompt, every value of the answer, then back fields.
    assert [(f.field, f.values) for f in question.back] == [
        ("literal", ("食",)),
        ("kunyomi", ("た.べる", "く.う")),
        ("meaning", ("eat",)),
    ]


def test_a_round_asks_every_item_once() -> None:
    settings = choice_settings((("literal",), "kunyomi"))
    cards = [kanji(1, "食", kun="た.べる"), *FILLER]
    for seed in range(20):
        items = [q.item_id for q in _play(cards, settings, Random(seed), 15)]
        for start in (0, 5, 10):
            assert set(items[start : start + 5]) == {1, 10, 11, 12, 13}


def test_never_the_same_item_twice_in_a_row() -> None:
    settings = choice_settings((("literal",), "onyomi"))
    for seed in range(20):
        items = [q.item_id for q in _play(FILLER, settings, Random(seed), 20)]
        assert all(a != b for a, b in pairwise(items))


def test_a_missed_item_comes_back_soon() -> None:
    settings = choice_settings((("literal",), "onyomi"))
    cards = [*FILLER, kanji(14, "川", on="セン"), kanji(15, "田", on="デン")]
    for seed in range(20):
        items = [
            q.item_id
            for q in _play(cards, settings, Random(seed), 12, wrong=frozenset({10}))
        ]
        # Every miss is asked again within the gap (sooner if a new round
        # happens to deal it), even in the middle of a round.
        misses = [i for i, item in enumerate(items) if item == 10]
        for miss, again in pairwise(misses):
            assert again - miss <= REVIEW_GAP
        assert len(misses) >= 3


def test_many_misses_dont_stop_the_deck() -> None:
    # Answering everything wrong: missed items come back, but every item of
    # the pool is still dealt within two rounds' worth of questions.
    settings = choice_settings((("literal",), "onyomi"))
    cards = [
        *FILLER,
        *(
            kanji(20 + i, c, on=o)
            for i, (c, o) in enumerate(
                [
                    ("川", "セン"),
                    ("田", "デン"),
                    ("石", "セキ"),
                    ("花", "カ2"),
                    ("森", "シン"),
                ]
            )
        ),
    ]
    everything = frozenset(c.item_id for c in cards)
    for seed in range(20):
        items = [
            q.item_id
            for q in _play(
                cards, settings, Random(seed), 2 * len(cards), wrong=everything
            )
        ]
        assert set(items) == everything


def test_items_added_mid_session_join_the_round() -> None:
    settings = choice_settings((("literal",), "onyomi"))
    rng = Random(3)
    history = _play(FILLER, settings, rng, 2)
    more = [*FILLER, kanji(14, "川", on="セン")]
    for _ in range(3):
        history.append(build_next_question(more, settings, history, rng))
    assert {q.item_id for q in history} == {10, 11, 12, 13, 14}


def test_option_count() -> None:
    settings = choice_settings((("literal",), "onyomi"), option_count=2)
    for question in _build(FILLER, settings):
        assert len(question.options) == 2


def test_fewer_options_when_the_pool_is_small() -> None:
    settings = choice_settings((("literal",), "onyomi"), option_count=8)
    for question in _build(FILLER, settings):
        assert len(question.options) == 4


def test_pool_too_small() -> None:
    settings = choice_settings((("literal",), "kunyomi"))
    with pytest.raises(ExercisePoolTooSmallError):
        build_next_question([FILLER[0]], settings, [], Random(0))
    # Items without the asked field don't count.
    with pytest.raises(ExercisePoolTooSmallError):
        build_next_question(
            [FILLER[0], kanji(2, "々"), kanji(3, "〆")], settings, [], Random(0)
        )


def test_only_directions_an_item_can_answer() -> None:
    settings = choice_settings((("literal",), "kunyomi"), (("literal",), "onyomi"))
    no_kun = kanji(1, "銀", on="ギン", meaning="silver")
    for question in _build([no_kun, *FILLER], settings):
        if question.item_id == 1:
            assert question.answer_field == "onyomi"


def test_shared_onyomi_is_never_a_distractor() -> None:
    # 校 and 高 are both コウ: when asked 校's on'yomi, こう can't come from 高.
    cards = [
        kanji(1, "校", on="コウ", meaning="school"),
        kanji(2, "高", on="コウ", meaning="tall"),
        *FILLER,
    ]
    settings = choice_settings((("literal",), "onyomi"))
    for question in _build(cards, settings):
        texts = _texts(question)
        assert texts.count("コウ") <= 1
        assert len({kana_key(t) for t in texts}) == len(texts)


def test_kanji_sharing_the_prompt_reading_isnt_a_wrong_option() -> None:
    # On'yomi → kanji: shown コウ, both 校 and 高 are right; neither can be wrong.
    cards = [
        kanji(1, "校", on="コウ"),
        kanji(2, "高", on="コウ"),
        *FILLER,
    ]
    settings = choice_settings((("onyomi",), "literal"))
    for question in _build(cards, settings):
        if question.item_id in (1, 2):
            assert {"校", "高"} & set(_texts(question)) == {
                question.options[question.correct_option].text
            }


def test_shared_kunyomi_in_katakana_or_with_okurigana() -> None:
    # The same kun'yomi written differently still matches: はし ≡ ハシ ≡ は.し
    cards = [
        kanji(1, "橋", kun="はし"),
        kanji(2, "箸", kun="ハシ"),
        kanji(3, "端", kun="は.し"),
        *FILLER,
    ]
    settings = choice_settings((("kunyomi",), "literal"))
    for question in _build(cards, settings):
        if question.item_id in (1, 2, 3):
            assert len({"橋", "箸", "端"} & set(_texts(question))) == 1


def test_homophones_arent_wrong_options() -> None:
    # Reading → writing: はし fits 橋 and 箸, so neither is a wrong option.
    cards = [
        word(1, "橋", "はし", "bridge"),
        word(2, "箸", "はし", "chopsticks"),
        word(3, "水", "みず", "water"),
        word(4, "山", "やま", "mountain"),
        word(5, "木", "き", "tree"),
    ]
    settings = choice_settings((("reading",), "writing"))
    for question in _build(cards, settings):
        if question.item_id in (1, 2):
            assert len({"橋", "箸"} & set(_texts(question))) == 1


def test_a_distractor_never_repeats_the_right_reading() -> None:
    # Meaning → reading for 箸: はし from 橋 would look wrong but is right.
    cards = [
        word(1, "橋", "はし", "bridge"),
        word(2, "箸", "はし", "chopsticks"),
        word(3, "水", "みず", "water"),
        word(4, "山", "やま", "mountain"),
    ]
    settings = choice_settings((("meaning",), "reading"))
    for question in _build(cards, settings):
        assert _texts(question).count("はし") <= 1


def test_synonyms_and_their_readings() -> None:
    # Meaning → reading for 話す ("to speak"): 言う also means "to speak", so
    # いう is right too, and is rejected even when it comes from 云う.
    cards = [
        word(1, "話す", "はなす", "to speak", "to talk"),
        word(2, "言う", "いう", "to say", "to speak"),
        word(3, "云う", "いう", "to say"),
        word(4, "水", "みず", "water"),
        word(5, "山", "やま", "mountain"),
        word(6, "木", "き", "tree"),
    ]
    settings = choice_settings((("meaning",), "reading"))
    for question in _build(cards, settings):
        if question.item_id == 1:
            assert "いう" not in _texts(question)


def test_synonyms_as_options() -> None:
    # Writing → meaning for 話す: 言う's meaning shares "to speak", so it's out.
    cards = [
        word(1, "話す", "はなす", "to speak", "to talk"),
        word(2, "言う", "いう", "to say", "to speak"),
        word(3, "水", "みず", "water"),
        word(4, "山", "やま", "mountain"),
    ]
    settings = choice_settings((("writing",), "meaning"))
    for question in _build(cards, settings):
        if question.item_id in (1, 2):
            meanings = [t for t in _texts(question) if "speak" in t]
            assert len(meanings) == 1


def test_same_spelling() -> None:
    # Two entries spelled 上手 (different readings): reading → writing never
    # offers 上手 as a wrong option for the other one.
    cards = [
        word(1, "上手", "じょうず", "skilful"),
        word(2, "上手", "うわて", "upper part"),
        word(3, "水", "みず", "water"),
        word(4, "山", "やま", "mountain"),
    ]
    settings = choice_settings((("reading",), "writing"))
    for question in _build(cards, settings):
        assert _texts(question).count("上手") <= 1


def test_a_word_is_asked_and_offered_by_its_usual_reading() -> None:
    # 山 also reads ヤマ and 川 がわ: those variants are never asked or offered,
    # but がわ still can't be offered as a wrong option for 川.
    cards = [
        word(1, "山", "やま ヤマ", "mountain"),
        word(2, "川", "かわ がわ", "river"),
        word(3, "水", "みず", "water"),
        word(4, "木", "き", "tree"),
    ]
    settings = choice_settings((("meaning",), "reading"))
    for question in _build(cards, settings):
        texts = _texts(question)
        assert "ヤマ" not in texts
        assert "がわ" not in texts

    reverse = choice_settings((("reading",), "meaning"))
    for question in _build(cards, reverse):
        if question.item_id == 2:
            assert question.prompt[0].values == ("かわ",)  # front: usual form
            assert ("reading", ("かわ", "がわ")) in [
                (f.field, f.values) for f in question.back
            ]


def test_no_unambiguous_option_skips_the_item() -> None:
    # Every item reads はし: no wrong option exists, so no question.
    cards = [kanji(1, "橋", kun="はし"), kanji(2, "箸", kun="はし")]
    settings = choice_settings((("kunyomi",), "literal"))
    with pytest.raises(ExercisePoolTooSmallError):
        build_next_question(cards, settings, [], Random(0))


def test_same_seed_same_session() -> None:
    settings = choice_settings((("literal",), "kunyomi"), (("kunyomi",), "literal"))
    first = _play(FILLER, settings, Random(42), 10)
    again = _play(FILLER, settings, Random(42), 10)
    assert first == again
