# Hiragana ぁ-ゖ (U+3041-U+3096) and katakana ァ-ヶ (U+30A1-U+30F6) are the same
# syllables 0x60 code points apart.
_OFFSET = 0x60
_HIRAGANA = (0x3041, 0x3096)
_KATAKANA = (0x30A1, 0x30F6)


def hiragana_to_katakana(text: str) -> str:
    """Convert the hiragana in `text` to katakana; other characters are kept."""
    lo, hi = _HIRAGANA
    return "".join(chr(ord(c) + _OFFSET) if lo <= ord(c) <= hi else c for c in text)


def katakana_to_hiragana(text: str) -> str:
    """Convert the katakana in `text` to hiragana; other characters are kept."""
    lo, hi = _KATAKANA
    return "".join(chr(ord(c) - _OFFSET) if lo <= ord(c) <= hi else c for c in text)
