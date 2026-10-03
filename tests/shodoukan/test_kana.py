from shodoukan.utils.kana import hiragana_to_katakana, katakana_to_hiragana


def test_hiragana_to_katakana():
    assert hiragana_to_katakana("かい") == "カイ"
    assert hiragana_to_katakana("しょく") == "ショク"


def test_katakana_to_hiragana():
    assert katakana_to_hiragana("スイ") == "すい"


def test_other_characters_are_kept():
    assert hiragana_to_katakana("た.べるー水") == "タ.ベルー水"
    assert katakana_to_hiragana("た.ベル") == "た.べる"
