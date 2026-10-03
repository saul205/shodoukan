import pytest

from shodoukan_practice.domain.gateways import KanaForms
from shodoukan_practice.infrastructure.dictionary import ShodoukanKanaGateway

gateway = ShodoukanKanaGateway()


@pytest.mark.parametrize(
    ("text", "hiragana", "katakana"),
    [
        ("taberu", "たべる", "タベル"),
        ("  Same ", "さめ", "サメ"),
        ("たべる", "たべる", "タベル"),
        ("パン", "ぱん", "パン"),
        ("ラーメン", "らーめん", "ラーメン"),
    ],
)
def test_romaji_and_kana_in_both_scripts(
    text: str, hiragana: str, katakana: str
) -> None:
    assert gateway.kana_forms(text) == KanaForms(hiragana, katakana)


@pytest.mark.parametrize("text", ["water", "食べる", "eat 2", "", "   "])
def test_text_that_is_not_kana_or_romaji(text: str) -> None:
    assert gateway.kana_forms(text) is None
