_TABLE: dict[str, str] = {
    # 3-char sequences (checked before 2-char)
    "sha": "しゃ", "shi": "し", "shu": "しゅ", "she": "しぇ", "sho": "しょ",
    "chi": "ち", "cha": "ちゃ", "chu": "ちゅ", "che": "ちぇ", "cho": "ちょ",
    "tsu": "つ",
    "tchi": "っち", "tcha": "っちゃ", "tchu": "っちゅ", "tcho": "っちょ",
    "kya": "きゃ", "kyu": "きゅ", "kyo": "きょ",
    "gya": "ぎゃ", "gyu": "ぎゅ", "gyo": "ぎょ",
    "nya": "にゃ", "nyu": "にゅ", "nyo": "にょ",
    "hya": "ひゃ", "hyu": "ひゅ", "hyo": "ひょ",
    "mya": "みゃ", "myu": "みゅ", "myo": "みょ",
    "rya": "りゃ", "ryu": "りゅ", "ryo": "りょ",
    "bya": "びゃ", "byu": "びゅ", "byo": "びょ",
    "pya": "ぴゃ", "pyu": "ぴゅ", "pyo": "ぴょ",
    "dya": "ぢゃ", "dyu": "ぢゅ", "dyo": "ぢょ",
    "zya": "じゃ", "zyu": "じゅ", "zyo": "じょ",
    # 2-char sequences
    "ka": "か", "ki": "き", "ku": "く", "ke": "け", "ko": "こ",
    "sa": "さ", "si": "し", "su": "す", "se": "せ", "so": "そ",
    "ta": "た", "ti": "ち", "tu": "つ", "te": "て", "to": "と",
    "na": "な", "ni": "に", "nu": "ぬ", "ne": "ね", "no": "の",
    "ha": "は", "hi": "ひ", "fu": "ふ", "hu": "ふ", "he": "へ", "ho": "ほ",
    "ma": "ま", "mi": "み", "mu": "む", "me": "め", "mo": "も",
    "ya": "や", "yu": "ゆ", "yo": "よ",
    "ra": "ら", "ri": "り", "ru": "る", "re": "れ", "ro": "ろ",
    "wa": "わ", "wo": "を",
    "ga": "が", "gi": "ぎ", "gu": "ぐ", "ge": "げ", "go": "ご",
    "za": "ざ", "zi": "じ", "zu": "ず", "ze": "ぜ", "zo": "ぞ",
    "ja": "じゃ", "ji": "じ", "ju": "じゅ", "je": "じぇ", "jo": "じょ",
    "da": "だ", "di": "ぢ", "du": "づ", "de": "で", "do": "ど",
    "ba": "ば", "bi": "び", "bu": "ぶ", "be": "べ", "bo": "ぼ",
    "pa": "ぱ", "pi": "ぴ", "pu": "ぷ", "pe": "ぺ", "po": "ぽ",
    "fa": "ふぁ", "fi": "ふぃ", "fe": "ふぇ", "fo": "ふぉ",
    # single vowels
    "a": "あ", "i": "い", "u": "う", "e": "え", "o": "お",
    # n — matches before consonants or end of string;
    # 2-char sequences like "na", "ni" take priority via longest-match
    "n": "ん",
}


def to_hiragana(text: str) -> str | None:
    """Convert Hepburn romaji to hiragana.

    Returns the hiragana string on full conversion, or None if any part of
    the input cannot be mapped (indicating the text is not romaji).
    """
    # Normalize: lowercase, "mb"/"mp" → "nb"/"np" (common phonetic variants),
    # apostrophes are syllable-boundary markers and are skipped in the loop.
    text = text.lower().replace("mb", "nb").replace("mp", "np")

    result: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]

        if c in "'-":
            i += 1
            continue

        # Double consonant → っ (not for vowels or 'n')
        if (
            c not in "aeioun"
            and i + 1 < len(text)
            and text[i + 1] == c
        ):
            result.append("っ")
            i += 1
            continue

        # Longest-match lookup: 4-char, then 3, 2, 1
        matched = False
        for length in (4, 3, 2, 1):
            chunk = text[i : i + length]
            if chunk in _TABLE:
                result.append(_TABLE[chunk])
                i += length
                matched = True
                break

        if not matched:
            return None

    return "".join(result) or None
