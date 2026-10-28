import pytest

from shodoukan_practice.domain.entities import Inflection
from shodoukan_practice.domain.gateways import Morpheme
from shodoukan_practice.domain.services import (
    gap_dictionary_forms,
    gap_inflection,
)
from shodoukan_practice.infrastructure.morphology import SudachiMorphologyGateway


@pytest.fixture(scope="module")
def gateway() -> SudachiMorphologyGateway:
    return SudachiMorphologyGateway()


def between(morphemes: list[Morpheme], text: str, word: str) -> list[Morpheme]:
    start = text.index(word)
    return [m for m in morphemes if m.start >= start and m.end <= start + len(word)]


def test_morphemes_cover_the_sentence(gateway: SudachiMorphologyGateway) -> None:
    text = "カーテンがゆっくり引かれた。"

    morphemes = gateway.morphemes(text)

    assert "".join(m.surface for m in morphemes) == text
    assert all(text[m.start : m.end] == m.surface for m in morphemes)
    assert [m.surface for m in morphemes][:3] == ["カーテン", "が", "ゆっくり"]


def test_an_inflected_verb(gateway: SudachiMorphologyGateway) -> None:
    text = "カーテンがゆっくり引かれた。"

    hikareta = between(gateway.morphemes(text), text, "引かれた")

    assert [m.lemma for m in hikareta] == ["引く", "れる", "た"]
    assert hikareta[0].pos[0] == "動詞"
    assert hikareta[0].conjugation_type == "五段-カ行"
    assert hikareta[0].reading == "ヒカ"
    assert gap_inflection(hikareta) == Inflection(endings=("れる", "た"), form="終止形")
    assert gap_dictionary_forms(hikareta)[0] == "引く"


def test_a_word_that_doesnt_inflect(gateway: SudachiMorphologyGateway) -> None:
    gakkou = between(gateway.morphemes("学校で勉強した。"), "学校で勉強した。", "学校")

    assert len(gakkou) == 1
    assert gakkou[0].conjugation_type is None
    assert gakkou[0].conjugation_form is None
    assert gakkou[0].reading == "ガッコウ"


def test_verbs_of_different_classes_share_a_form(
    gateway: SudachiMorphologyGateway,
) -> None:
    def form(text: str, word: str) -> Inflection | None:
        return gap_inflection(between(gateway.morphemes(text), text, word))

    assert form("酒を飲んだ。", "飲んだ") == form("パンを食べた。", "食べた")
    assert form("本を読んでいる。", "読んで") == form("パンを食べている。", "食べて")
    passive = form("名前を呼ばれた。", "呼ばれた")
    assert passive == form("全部食べられた。", "食べられた")


def test_kana_words_find_their_lemma(gateway: SudachiMorphologyGateway) -> None:
    text = "もう一度やってみる。"

    yatte = between(gateway.morphemes(text), text, "やって")

    assert yatte[0].lemma == "やる"


def test_a_counter_is_part_of_the_word(gateway: SudachiMorphologyGateway) -> None:
    text = "りんごを七つ買った。"

    assert gap_inflection(between(gateway.morphemes(text), text, "七つ")) == (
        Inflection(endings=(), form=None)
    )


def test_a_verb_before_a_noun_is_in_the_plain_form(
    gateway: SudachiMorphologyGateway,
) -> None:
    def form(text: str, word: str) -> Inflection | None:
        return gap_inflection(between(gateway.morphemes(text), text, word))

    assert form("走った人がいる。", "走った") == form("もう走った。", "走った")
