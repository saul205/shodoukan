_GLOSS_LANG = {
    "en": "eng",
    "es": "spa",
    "fr": "fre",
    "de": "ger",
    "ru": "rus",
    "nl": "dut",
    "hu": "hun",
    "sl": "slv",
}

_MEANING_LANG = {
    "en": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
}


def gloss_lang(iso1: str) -> str:
    return _GLOSS_LANG.get(iso1, iso1)


def meaning_lang(iso1: str) -> str:
    return _MEANING_LANG.get(iso1, iso1)
