_CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Extension A
    (0x20000, 0x2A6DF),  # CJK Extension B
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
]
_HIRAGANA = (0x3040, 0x309F)
_KATAKANA = (0x30A0, 0x30FF)


def contains_kanji(text: str) -> bool:
    return any(
        lo <= ord(c) <= hi
        for c in text
        for lo, hi in _CJK_RANGES
    )


def contains_kana(text: str) -> bool:
    return any(
        (_HIRAGANA[0] <= ord(c) <= _HIRAGANA[1])
        or (_KATAKANA[0] <= ord(c) <= _KATAKANA[1])
        for c in text
    )


def is_japanese(text: str) -> bool:
    return contains_kanji(text) or contains_kana(text)


def is_kanji_only(text: str) -> bool:
    return bool(text) and all(
        any(lo <= ord(c) <= hi for lo, hi in _CJK_RANGES) for c in text
    )


def is_romaji(text: str) -> bool:
    """True if text consists only of ASCII letters, apostrophes and hyphens."""
    return bool(text) and all(c.isalpha() and c.isascii() or c in "'-" for c in text)
