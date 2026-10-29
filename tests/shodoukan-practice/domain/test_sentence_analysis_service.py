import pytest

from shodoukan_practice.domain.entities import Inflection
from shodoukan_practice.domain.gateways import Morpheme
from shodoukan_practice.domain.services import (
    GapAnalysis,
    WordProposal,
    analyze_gap,
    candidate_forms,
    find_gap,
    propose_words,
    span_morphemes,
)

VERB = ("動詞", "一般")
NOUN = ("名詞", "普通名詞", "一般")


def sentence(
    *parts: tuple[str, str, str, tuple[str, ...], str | None],
) -> list[Morpheme]:
    """Morphemes from (surface, lemma, reading, pos, form), offsets in order."""
    morphemes = []
    start = 0
    for surface, lemma, reading, pos, form in parts:
        morphemes.append(
            Morpheme(
                surface=surface,
                lemma=lemma,
                reading=reading,
                pos=pos,
                conjugation_type="x" if form else None,
                conjugation_form=form,
                start=start,
                end=start + len(surface),
            )
        )
        start += len(surface)
    return morphemes


# 風邪を引いた。
KAZE = sentence(
    ("風邪", "風邪", "カゼ", NOUN, None),
    ("を", "を", "ヲ", ("助詞", "格助詞"), None),
    ("引い", "引く", "ヒイ", VERB, "連用形-イ音便"),
    ("た", "た", "タ", ("助動詞",), "終止形-一般"),
    ("。", "。", "。", ("補助記号", "句点"), None),
)


def test_span_morphemes() -> None:
    assert span_morphemes(KAZE, 3, 6) == KAZE[2:4]  # 引いた
    assert span_morphemes(KAZE, 3, 4) is None  # cuts 引い


def test_analyze_an_inflected_gap() -> None:
    assert analyze_gap(KAZE[2:4], ["引く", "ひく"]) == GapAnalysis(
        lemma="引く",
        reading="ひいた",
        pos=VERB,
        inflection=Inflection(endings=("た",), form="終止形"),
    )


def test_the_lemma_is_the_linked_words_form() -> None:
    # 共に: the head's lemma (共) isn't the word; the gap as written is.
    tomoni = sentence(
        ("共", "共", "トモ", NOUN, None), ("に", "に", "ニ", ("助詞",), None)
    )

    assert analyze_gap(tomoni, ["共に", "ともに"]).lemma == "共に"
    assert analyze_gap(tomoni).lemma == "共"  # unlinked: the best guess


def test_a_katakana_word_keeps_its_reading_in_katakana() -> None:
    curtain = sentence(("カーテン", "カーテン", "カーテン", NOUN, None))

    assert analyze_gap(curtain).reading == "カーテン"


def test_a_gap_needs_morphemes() -> None:
    with pytest.raises(ValueError):
        analyze_gap([])


def test_find_an_inflected_word() -> None:
    assert find_gap(KAZE, ["引く", "ひく"]) == (3, 6)  # 引いた
    assert find_gap(KAZE, ["ひく"]) is None  # 引いた is written in kanji
    assert find_gap(KAZE, ["風邪"]) == (0, 2)
    assert find_gap(KAZE, ["を"]) is None  # not a content word
    assert find_gap(KAZE, ["飲む"]) is None


def test_find_a_kana_word_by_its_reading() -> None:
    # もうやった: a word written in kana is found by its reading.
    yatta = sentence(
        ("もう", "もう", "モウ", ("副詞",), None),
        ("やっ", "やる", "ヤッ", VERB, "連用形-促音便"),
        ("た", "た", "タ", ("助動詞",), "終止形-一般"),
    )

    assert find_gap(yatta, ["遣る", "やる"]) == (2, 5)


def test_find_skips_taken_spans() -> None:
    # 引くと引く: the first one is taken.
    twice = sentence(
        ("引く", "引く", "ヒク", VERB, "終止形-一般"),
        ("と", "と", "ト", ("助詞", "接続助詞"), None),
        ("引く", "引く", "ヒク", VERB, "終止形-一般"),
    )

    assert find_gap(twice, ["引く"], taken=[(0, 2)]) == (3, 5)
    assert find_gap(twice, ["引く"], taken=[(0, 2), (3, 5)]) is None


def test_te_form_is_part_of_the_word() -> None:
    # 読んでいる: で joins 読ん, いる (a verb) doesn't.
    yonde = sentence(
        ("読ん", "読む", "ヨン", VERB, "連用形-撥音便"),
        ("で", "で", "デ", ("助詞", "接続助詞"), None),
        ("いる", "いる", "イル", ("動詞", "非自立可能"), "終止形-一般"),
    )

    assert find_gap(yonde, ["読む"]) == (0, 3)


def test_find_an_expression_of_several_words() -> None:
    # 持っていってね: 持っ + て + いっ + て + ね, the word 持っていく.
    motte = sentence(
        ("持っ", "持つ", "モッ", VERB, "連用形-促音便"),
        ("て", "て", "テ", ("助詞", "接続助詞"), None),
        ("いっ", "いく", "イッ", ("動詞", "非自立可能"), "連用形-促音便"),
        ("て", "て", "テ", ("助詞", "接続助詞"), None),
        ("ね", "ね", "ネ", ("助詞", "終助詞"), None),
    )

    assert find_gap(motte, ["持っていく", "もっていく"]) == (0, 6)  # 持っていって
    assert find_gap(motte, ["持つ"]) == (0, 3)  # 持って


def test_propose_the_library_words_of_a_sentence() -> None:
    # 日本語を引いた: 日本語 (a longer match than 日本), 引く inflected.
    nihongo = sentence(
        ("日本", "日本", "ニホン", NOUN, None),
        ("語", "語", "ゴ", ("接尾辞",), None),
        ("を", "を", "ヲ", ("助詞", "格助詞"), None),
        ("引い", "引く", "ヒイ", VERB, "連用形-イ音便"),
        ("た", "た", "タ", ("助動詞",), "終止形-一般"),
    )
    library = {"日本": [1], "日本語": [2], "引く": [3]}

    assert {"日本", "日本語", "引く"} <= candidate_forms(nihongo)
    assert propose_words(nihongo, library) == [
        WordProposal(start=0, end=3, form="日本語", entry_ids=(2,), certain=True),
        WordProposal(start=4, end=7, form="引く", entry_ids=(3,), certain=True),
    ]
    assert propose_words(nihongo, {}) == []


def test_a_kana_only_match_is_a_guess() -> None:
    # はしを渡る: はし may be 橋 or 箸, found by their reading only.
    hashi = sentence(
        ("はし", "はし", "ハシ", NOUN, None),
        ("を", "を", "ヲ", ("助詞", "格助詞"), None),
    )

    assert propose_words(hashi, {"はし": [5, 6]}) == [
        WordProposal(start=0, end=2, form="はし", entry_ids=(5, 6), certain=False)
    ]
