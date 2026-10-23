from shodoukan.utils.detect import contains_kana, is_romaji
from shodoukan.utils.kana import hiragana_to_katakana, katakana_to_hiragana
from shodoukan.utils.romaji import to_hiragana

from ...domain.gateways import KanaForms, KanaGateway


class ShodoukanKanaGateway(KanaGateway):
    """Kana conversion with the `shodoukan` library's romaji and kana tools."""

    def kana_forms(self, text: str) -> KanaForms | None:
        text = text.strip()
        if not text:
            return None
        if is_romaji(text):
            hiragana = to_hiragana(text)
        elif all(contains_kana(char) for char in text):
            hiragana = katakana_to_hiragana(text)
        else:
            return None
        if not hiragana:
            return None
        return KanaForms(hiragana=hiragana, katakana=hiragana_to_katakana(hiragana))
