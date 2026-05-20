import pytest

from shodoukan.utils.romaji import to_hiragana


@pytest.mark.parametrize("romaji, expected", [
    ("taberu", "たべる"),
    ("sushi", "すし"),
    ("karate", "からて"),
    ("anime", "あにめ"),
    ("sakura", "さくら"),
    ("tsuki", "つき"),
    ("ramen", "らめん"),
    ("nani", "なに"),
    ("sake", "さけ"),
    ("manga", "まんが"),
])
def test_common_words(romaji, expected):
    assert to_hiragana(romaji) == expected


@pytest.mark.parametrize("romaji, expected", [
    ("kitte", "きって"),
    ("itte", "いって"),
    ("zasshi", "ざっし"),
    ("cchi", "っち"),
    ("tchi", "っち"),
    ("kekka", "けっか"),
])
def test_double_consonants(romaji, expected):
    assert to_hiragana(romaji) == expected


@pytest.mark.parametrize("romaji, expected", [
    ("sannin", "さんにん"),
    ("shinbun", "しんぶん"),
    ("shimbun", "しんぶん"),  # mb → nb normalization
    ("onsen", "おんせん"),
    ("kanpai", "かんぱい"),   # mp → np normalization
])
def test_n_handling(romaji, expected):
    assert to_hiragana(romaji) == expected


@pytest.mark.parametrize("romaji, expected", [
    ("sha", "しゃ"),
    ("shu", "しゅ"),
    ("sho", "しょ"),
    ("cha", "ちゃ"),
    ("chi", "ち"),
    ("chu", "ちゅ"),
    ("cho", "ちょ"),
    ("kya", "きゃ"),
    ("ryu", "りゅ"),
    ("nyo", "にょ"),
])
def test_digraphs(romaji, expected):
    assert to_hiragana(romaji) == expected


@pytest.mark.parametrize("romaji", [
    "water",
    "beer",
    "english",
    "xyz",
])
def test_unconvertible_returns_none(romaji):
    assert to_hiragana(romaji) is None


def test_case_insensitive():
    assert to_hiragana("TABERU") == "たべる"
    assert to_hiragana("Sushi") == "すし"


def test_apostrophe_boundary():
    assert to_hiragana("nan'yo") == "なんよ"
