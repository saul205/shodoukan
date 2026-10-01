"""Anti-corruption layer: shodoukan dictionary models -> practice entities.

Only what the practice app needs is copied. Dictionary row ids aren't kept
on nested items (the snapshot gets its own ids when stored); the entry keeps
`source_entry_id` and the kanji its `literal` as the link back. Dropped on
purpose: priority tags, cross references, search scores and example
provenance (`source_name`, `source_id`).
"""

from uuid import UUID

from shodoukan.models.entry import Entry, Example, Sense
from shodoukan.models.kanji import Kanji

from ...domain.entities import (
    PracticeEntry,
    PracticeExample,
    PracticeExampleSentence,
    PracticeGloss,
    PracticeKanji,
    PracticeKanjiMeaning,
    PracticeKanjiReading,
    PracticeReading,
    PracticeReadingItem,
    PracticeSense,
)


def shodoukan_entry_to_practice(entry: Entry, user_id: UUID) -> PracticeEntry:
    return PracticeEntry(
        id=None,
        user_id=user_id,
        source_entry_id=entry.id,
        kanji_readings=[
            PracticeKanjiReading(id=None, kanji=kr.kanji, info=list(kr.info))
            for kr in entry.kanji_readings
        ],
        readings=[
            PracticeReading(
                id=None,
                text=r.text,
                no_kanji=r.no_kanji,
                info=list(r.info),
                restricted_to=list(r.restricted_to),
            )
            for r in entry.readings
        ],
        senses=[_sense(s) for s in entry.senses],
        jlpt=entry.jlpt,
        is_common=entry.is_common,
    )


def _sense(sense: Sense) -> PracticeSense:
    return PracticeSense(
        id=None,
        pos=list(sense.pos),
        misc=list(sense.misc),
        dialects=list(sense.dialects),
        info=list(sense.info),
        glosses=[
            PracticeGloss(id=None, text=g.text, lang=g.lang, type=g.type)
            for g in sense.glosses
        ],
        examples=[_example(ex) for ex in sense.examples],
    )


def _example(example: Example) -> PracticeExample:
    return PracticeExample(
        id=None,
        text=example.text,
        sentences=[
            PracticeExampleSentence(lang=s.lang, text=s.text) for s in example.sentences
        ],
    )


def shodoukan_kanji_to_practice(kanji: Kanji, user_id: UUID) -> PracticeKanji:
    return PracticeKanji(
        id=None,
        user_id=user_id,
        literal=kanji.literal,
        grade=kanji.grade,
        stroke_count=kanji.stroke_count,
        freq=kanji.freq,
        jlpt=kanji.jlpt,
        on_readings=_items(kanji.on_readings),
        kun_readings=_items(kanji.kun_readings),
        nanori=_items(kanji.nanori),
        meanings=[
            PracticeKanjiMeaning(id=None, text=m.text, lang=m.lang)
            for m in kanji.meanings
        ],
    )


def _items(texts: list[str]) -> list[PracticeReadingItem]:
    return [PracticeReadingItem(id=None, text=text) for text in texts]
