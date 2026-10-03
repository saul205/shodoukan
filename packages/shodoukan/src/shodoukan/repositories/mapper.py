"""Mapping functions from SQLAlchemy ORM objects to Pydantic domain models."""

import json

from shodoukan.db.orm import EntryORM, KanjiORM
from shodoukan.models.entry import (
    CrossReference,
    Entry,
    Example,
    ExampleSentence,
    Gloss,
    KanjiReading,
    Reading,
    Sense,
)
from shodoukan.models.kanji import Kanji, KanjiMeaning


def _json(value: str) -> list[str]:
    return json.loads(value) if value else []


def entry_to_domain(e: EntryORM) -> Entry:
    return Entry(
        id=e.id,
        kanji_readings=[
            KanjiReading(
                id=kr.id,
                kanji=kr.kanji,
                priority=_json(kr.priority),
                info=_json(kr.info),
            )
            for kr in e.kanji_readings
        ],
        readings=[
            Reading(
                id=r.id,
                text=r.text,
                no_kanji=bool(r.no_kanji),
                priority=_json(r.priority),
                info=_json(r.info),
                restricted_to=[kr.kanji for kr in r.restrictions],
            )
            for r in e.readings
        ],
        senses=[
            Sense(
                id=s.id,
                pos=_json(s.pos),
                misc=_json(s.misc),
                dialects=_json(s.dialects),
                info=_json(s.info),
                glosses=[
                    Gloss(id=g.id, text=g.text, type=g.type, lang=g.lang)
                    for g in s.glosses
                ],
                cross_references=[
                    CrossReference(
                        reference=x.reference,
                        reading=x.reading,
                        sense_idx=x.sense_idx,
                    )
                    for x in s.cross_references
                ],
                examples=[
                    Example(
                        id=ex.id,
                        source_name=ex.source_name,
                        source_id=ex.source_id,
                        text=ex.text,
                        sentences=[
                            ExampleSentence(lang=sent.lang, text=sent.text)
                            for sent in ex.sentences
                        ],
                    )
                    for ex in s.examples
                ],
            )
            for s in e.senses
        ],
    )


def kanji_to_domain(k: KanjiORM) -> Kanji:
    return Kanji(
        literal=k.literal,
        grade=k.grade,
        stroke_count=k.stroke_count,
        freq=k.freq,
        jlpt=k.jlpt,
        on_readings=_json(k.on_readings),
        kun_readings=_json(k.kun_readings),
        nanori=_json(k.nanori),
        meanings=[KanjiMeaning(text=m.text, lang=m.lang) for m in k.meanings],
    )
