import pytest
from shodoukan.utils.detect import contains_kanji, contains_kana, is_japanese


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
