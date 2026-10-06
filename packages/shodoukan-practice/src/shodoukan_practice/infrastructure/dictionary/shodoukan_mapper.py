"""Anti-corruption layer: shodoukan dictionary models -> practice models.

Two translations: snapshots for import (practice entities) and search
results (the gateway's `Dictionary*` read models). Only what the practice
app needs is copied. Dictionary row ids aren't kept
on nested items (the snapshot gets its own ids when stored); the entry keeps
`source_entry_id` and the kanji its `literal` as the link back. Dropped on
purpose: priority tags, cross references, search scores and example
provenance (`source_name`, `source_id`).
"""

from uuid import UUID

from shodoukan.models.entry import Entry, Example, Page, Sense
from shodoukan.models.kanji import Kanji, KanjiStrokes
from shodoukan.models.search import SearchResult
from shodoukan.utils.svg_path import path_points

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
    ReferenceKanji,
    ReferenceStroke,
)
from ...domain.gateways import (
    DictionaryCrossReference,
    DictionaryEntry,
    DictionaryEntryPage,
    DictionaryExample,
    DictionaryExampleSentence,
    DictionaryGloss,
    DictionaryKanji,
    DictionaryKanjiMeaning,
    DictionaryKanjiReading,
    DictionaryKanjiStroke,
    DictionaryKanjiStrokes,
    DictionaryReading,
    DictionarySearchResult,
    DictionarySense,
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


# --- Search results -> read models


def shodoukan_search_to_dictionary(result: SearchResult) -> DictionarySearchResult:
    return DictionarySearchResult(
        entries=shodoukan_entry_page_to_dictionary(result.entries),
        kanji=[shodoukan_kanji_to_dictionary(k) for k in result.kanji],
    )


def shodoukan_entry_page_to_dictionary(page: Page[Entry]) -> DictionaryEntryPage:
    return DictionaryEntryPage(
        items=[shodoukan_entry_to_dictionary(e) for e in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


def shodoukan_entry_to_dictionary(entry: Entry) -> DictionaryEntry:
    return DictionaryEntry(
        id=entry.id,
        kanji_readings=[
            DictionaryKanjiReading(kanji=kr.kanji, info=list(kr.info))
            for kr in entry.kanji_readings
        ],
        readings=[
            DictionaryReading(
                text=r.text,
                no_kanji=r.no_kanji,
                info=list(r.info),
                restricted_to=list(r.restricted_to),
            )
            for r in entry.readings
        ],
        senses=[_dictionary_sense(s) for s in entry.senses],
        jlpt=entry.jlpt,
        is_common=entry.is_common,
    )


def _dictionary_sense(sense: Sense) -> DictionarySense:
    return DictionarySense(
        pos=list(sense.pos),
        misc=list(sense.misc),
        dialects=list(sense.dialects),
        info=list(sense.info),
        glosses=[
            DictionaryGloss(text=g.text, lang=g.lang, type=g.type)
            for g in sense.glosses
        ],
        cross_references=[
            DictionaryCrossReference(
                reference=x.reference, reading=x.reading, sense_index=x.sense_idx
            )
            for x in sense.cross_references
        ],
        examples=[
            DictionaryExample(
                text=ex.text,
                sentences=[
                    DictionaryExampleSentence(lang=s.lang, text=s.text)
                    for s in ex.sentences
                ],
            )
            for ex in sense.examples
        ],
    )


def shodoukan_kanji_to_dictionary(kanji: Kanji) -> DictionaryKanji:
    return DictionaryKanji(
        literal=kanji.literal,
        grade=kanji.grade,
        stroke_count=kanji.stroke_count,
        freq=kanji.freq,
        jlpt=kanji.jlpt,
        on_readings=list(kanji.on_readings),
        kun_readings=list(kanji.kun_readings),
        nanori=list(kanji.nanori),
        meanings=[
            DictionaryKanjiMeaning(text=m.text, lang=m.lang) for m in kanji.meanings
        ],
    )


def shodoukan_kanji_strokes_to_dictionary(
    strokes: KanjiStrokes,
) -> DictionaryKanjiStrokes:
    return DictionaryKanjiStrokes(
        literal=strokes.literal,
        strokes=[
            DictionaryKanjiStroke(path=s.path, label=s.label) for s in strokes.strokes
        ],
    )


# Distance between the points of a reference stroke, in KanjiVG units (the
# kanji is 109 wide). It only sets how finely a curve is followed; grading
# resamples every stroke to its own number of points.
REFERENCE_POINT_SPACING = 2.0


def shodoukan_strokes_to_reference(strokes: KanjiStrokes) -> ReferenceKanji:
    """A kanji's strokes to grade drawings against: each stroke's path and
    number place, and its centre line as points."""
    return ReferenceKanji(
        literal=strokes.literal,
        strokes=tuple(
            ReferenceStroke(
                path=s.path,
                label=s.label,
                points=tuple(path_points(s.path, REFERENCE_POINT_SPACING)),
            )
            for s in strokes.strokes
        ),
    )
