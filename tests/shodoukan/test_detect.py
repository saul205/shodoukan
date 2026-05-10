import pytest
from shodoukan.utils.detect import contains_kanji, contains_kana, is_japanese, is_romaji


@pytest.mark.parametrize("text, expected", [
    ("eat", False),
    ("sushi", False),
    ("たべる", False),
    ("タベル", False),
    ("食べる", True),
    ("食", True),
    ("日本語", True),
])
def test_contains_kanji(text, expected):
    assert contains_kanji(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("eat", False),
    ("sushi", False),
    ("たべる", True),
    ("タベル", True),
    ("食べる", True),
    ("食", False),
])
def test_contains_kana(text, expected):
    assert contains_kana(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("eat", False),
    ("rice field", False),
    ("たべる", True),
    ("タベル", True),
    ("食べる", True),
    ("食", True),
    ("sushi 寿司", True),
])
def test_is_japanese(text, expected):
    assert is_japanese(text) == expected


@pytest.mark.parametrize("text, expected", [
    ("taberu", True),
    ("sushi", True),
    ("nan'yo", True),
    ("eat", True),        # ASCII — treated as potential romaji; to_hiragana decides
    ("たべる", False),
    ("食べる", False),
    ("sushi 寿司", False),
    ("", False),
])
def test_is_romaji(text, expected):
    assert is_romaji(text) == expected
