"""Read the fields an exercise studies from a library item, and compare them.

Only enabled parts count. A field can have several values (two readings, two
spellings); each value keeps its text for display and the normalized keys it
is compared by, so a wrong option is never a hidden right answer:

- kana: katakana as hiragana, okurigana dots and affix dashes removed
  (ショク ≡ しょく, た.べる ≡ たべる);
- meanings: one key per gloss, lower-cased, without a leading "to " or text in
  parentheses (a meaning matches another if they share a gloss);
- spellings and kanji: the text as is.

See docs/practice/technical/exercises.md.
"""

import re
from dataclasses import dataclass

from ..entities import PracticeEntry, PracticeKanji, StudyField
from ..repositories import EntryStudyText, KanjiStudyText

_KATAKANA_START = ord("ァ")
_KATAKANA_END = ord("ヶ")
_KATAKANA_TO_HIRAGANA = ord("ぁ") - ord("ァ")
_PARENTHESES = re.compile(r"\([^)]*\)")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class FieldValue:
    """One value of a field: shown as `text`, compared by `keys`."""

    text: str
    keys: frozenset[str]


@dataclass(frozen=True)
class StudyCard:
    """An item's values for the fields an exercise uses.

    A field with no values is missing (a kana-only word has no writing).
    Every value is shown and compared, but only the first one of a
    `first_only` field is asked or offered: a word's other spellings and
    readings are variants (ヤマ for やま), while each reading of a kanji is
    worth asking.
    """

    item_id: int
    values: dict[StudyField, tuple[FieldValue, ...]]
    first_only: frozenset[StudyField] = frozenset()

    def get(self, field: StudyField) -> tuple[FieldValue, ...]:
        return self.values.get(field, ())

    def has(self, *fields: StudyField) -> bool:
        return all(self.get(field) for field in fields)

    def answers(self, field: StudyField) -> tuple[FieldValue, ...]:
        """The values that can be asked or offered as options."""
        values = self.get(field)
        return values[:1] if field in self.first_only else values

    def keys(self, field: StudyField) -> frozenset[str]:
        """Every key of every value of `field`."""
        return frozenset().union(*(value.keys for value in self.get(field)))


def kanji_literal(card: StudyCard) -> str | None:
    """The kanji of a kanji card; None for a word's."""
    values = card.answers("literal")
    return values[0].text if values else None


def kana_key(text: str) -> str:
    """Hiragana, without okurigana dots or affix dashes."""
    hiragana = "".join(
        chr(ord(char) + _KATAKANA_TO_HIRAGANA)
        if _KATAKANA_START <= ord(char) <= _KATAKANA_END
        else char
        for char in text
    )
    return hiragana.replace(".", "").replace("-", "")


def gloss_key(text: str) -> str:
    """A gloss as compared: lower-case, no "to ", no parentheses."""
    text = _PARENTHESES.sub(" ", text.lower())
    text = _SPACES.sub(" ", text).strip()
    return text.removeprefix("to ").strip()


def _kana(texts: list[str]) -> tuple[FieldValue, ...]:
    return tuple(FieldValue(text, frozenset({kana_key(text)})) for text in texts)


def _as_is(texts: list[str]) -> tuple[FieldValue, ...]:
    return tuple(FieldValue(text, frozenset({text})) for text in texts)


def _meaning(glosses: list[str], separator: str) -> tuple[FieldValue, ...]:
    """All glosses as one value, keyed by each gloss."""
    if not glosses:
        return ()
    keys = frozenset(key for key in map(gloss_key, glosses) if key)
    return (FieldValue(separator.join(glosses), keys),)


def entry_study_text(entry: PracticeEntry, meaning_lang: str) -> EntryStudyText:
    """What an exercise studies of a loaded entry, as
    `PracticeEntryRepository.study_texts` reads it from the library.
    `meaning_lang` as entry glosses store it (ISO 639-2, e.g. "eng")."""
    assert entry.id is not None, "only stored entries are studied"
    sense_glosses = (
        tuple(g.text for g in sense.glosses if g.enabled and g.lang == meaning_lang)
        for sense in entry.senses
        if sense.enabled
    )
    return EntryStudyText(
        id=entry.id,
        spellings=tuple(k.kanji for k in entry.kanji_readings if k.enabled),
        readings=tuple(r.text for r in entry.readings if r.enabled),
        sense_glosses=tuple(glosses for glosses in sense_glosses if glosses),
    )


def kanji_study_text(kanji: PracticeKanji, meaning_lang: str) -> KanjiStudyText:
    """What an exercise studies of a loaded kanji, as
    `PracticeKanjiRepository.study_texts` reads it from the library.
    `meaning_lang` as kanji meanings store it (ISO 639-1, e.g. "en")."""
    assert kanji.id is not None, "only stored kanji are studied"
    return KanjiStudyText(
        id=kanji.id,
        literal=kanji.literal,
        onyomi=tuple(r.text for r in kanji.on_readings if r.enabled),
        kunyomi=tuple(r.text for r in kanji.kun_readings if r.enabled),
        meanings=tuple(
            m.text for m in kanji.meanings if m.enabled and m.lang == meaning_lang
        ),
    )


def entry_card(entry: EntryStudyText, fields: frozenset[StudyField]) -> StudyCard:
    """The meaning is the glosses of the first enabled sense that has enabled
    glosses in the language. Only the first enabled spelling and reading are
    asked: the dictionary lists a word's usual form first, and the user can
    disable it to be asked another.
    """
    values: dict[StudyField, tuple[FieldValue, ...]] = {}
    if "writing" in fields:
        values["writing"] = _as_is(list(entry.spellings))
    if "reading" in fields:
        values["reading"] = _kana(list(entry.readings))
    if "meaning" in fields:
        glosses = entry.sense_glosses[0] if entry.sense_glosses else ()
        values["meaning"] = _meaning(list(glosses), "; ")
    return StudyCard(entry.id, values, first_only=frozenset({"writing", "reading"}))


def kanji_card(kanji: KanjiStudyText, fields: frozenset[StudyField]) -> StudyCard:
    values: dict[StudyField, tuple[FieldValue, ...]] = {}
    if "literal" in fields:
        values["literal"] = _as_is([kanji.literal])
    if "onyomi" in fields:
        values["onyomi"] = _kana(list(kanji.onyomi))
    if "kunyomi" in fields:
        values["kunyomi"] = _kana(list(kanji.kunyomi))
    if "meaning" in fields:
        values["meaning"] = _meaning(list(kanji.meanings), ", ")
    return StudyCard(kanji.id, values)


def entry_label(entry: PracticeEntry) -> tuple[str, str | None]:
    """How a word is named outside a card (e.g. in statistics): its usual
    form, as asked (`entry_card`'s first spelling, else its first reading),
    and its reading when the form is a spelling. With every part disabled,
    the dictionary's first spelling or reading."""
    card = entry_card(entry_study_text(entry, ""), frozenset({"writing", "reading"}))
    writings, readings = card.answers("writing"), card.answers("reading")
    reading = readings[0].text if readings else None
    if writings:
        return writings[0].text, reading
    if reading is not None:
        return reading, None
    if entry.kanji_readings:
        return entry.kanji_readings[0].kanji, None
    return entry.readings[0].text, None
