"""PracticeEntry <-> practice_entries and its nested tables.

List order in the domain is stored as `position` (the list index).
"""

from typing import Literal

from ....domain.entities import (
    PracticeEntry,
    PracticeExample,
    PracticeExampleSentence,
    PracticeGloss,
    PracticeKanjiReading,
    PracticeReading,
    PracticeSense,
)
from ..orm import (
    PracticeEntryKanjiReadingORM,
    PracticeEntryORM,
    PracticeEntryReadingORM,
    PracticeExampleORM,
    PracticeExampleSentenceORM,
    PracticeGlossORM,
    PracticeSenseORM,
)


def _origin(value: str) -> Literal["imported", "added"]:
    if value == "imported":
        return "imported"
    if value == "added":
        return "added"
    raise ValueError(f"unknown origin {value!r}")


def practice_entry_to_domain(row: PracticeEntryORM) -> PracticeEntry:
    return PracticeEntry(
        id=row.id,
        user_id=row.user_id,
        source_entry_id=row.source_entry_id,
        original_id=row.original_id,
        source_id=row.source_id,
        kanji_readings=[
            PracticeKanjiReading(
                id=kr.id,
                kanji=kr.kanji,
                info=kr.info,
                enabled=kr.enabled,
                origin=_origin(kr.origin),
                original_id=kr.original_id,
                source_id=kr.source_id,
                edited_id=kr.edited_id,
                source_collection_id=kr.source_collection_id,
            )
            for kr in row.kanji_readings
        ],
        readings=[
            PracticeReading(
                id=r.id,
                text=r.text,
                no_kanji=r.no_kanji,
                info=r.info,
                restricted_to=r.restricted_to,
                enabled=r.enabled,
                origin=_origin(r.origin),
                original_id=r.original_id,
                source_id=r.source_id,
                edited_id=r.edited_id,
                source_collection_id=r.source_collection_id,
            )
            for r in row.readings
        ],
        senses=[_sense_to_domain(s) for s in row.senses],
        jlpt=row.jlpt,
        is_common=row.is_common,
        is_active=row.is_active,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _sense_to_domain(row: PracticeSenseORM) -> PracticeSense:
    return PracticeSense(
        id=row.id,
        notes=row.notes,
        pos=row.pos,
        misc=row.misc,
        dialects=row.dialects,
        info=row.info,
        enabled=row.enabled,
        origin=_origin(row.origin),
        original_id=row.original_id,
        source_id=row.source_id,
        glosses=[
            PracticeGloss(
                id=g.id,
                text=g.text,
                lang=g.lang,
                type=g.type,
                enabled=g.enabled,
                origin=_origin(g.origin),
                original_id=g.original_id,
                source_id=g.source_id,
                edited_id=g.edited_id,
                source_collection_id=g.source_collection_id,
            )
            for g in row.glosses
        ],
        examples=[
            PracticeExample(
                id=ex.id,
                text=ex.text,
                sentences=[
                    PracticeExampleSentence(lang=s.lang, text=s.text)
                    for s in ex.sentences
                ],
                enabled=ex.enabled,
                origin=_origin(ex.origin),
                original_id=ex.original_id,
                source_id=ex.source_id,
                edited_id=ex.edited_id,
                source_collection_id=ex.source_collection_id,
            )
            for ex in row.examples
        ],
    )


def practice_entry_to_db(entity: PracticeEntry) -> PracticeEntryORM:
    return PracticeEntryORM(
        id=entity.id,
        user_id=entity.user_id,
        source_entry_id=entity.source_entry_id,
        original_id=entity.original_id,
        source_id=entity.source_id,
        kanji_readings=[
            PracticeEntryKanjiReadingORM(
                id=kr.id,
                position=i,
                kanji=kr.kanji,
                info=kr.info,
                enabled=kr.enabled,
                origin=kr.origin,
                original_id=kr.original_id,
                source_id=kr.source_id,
                edited_id=kr.edited_id,
                source_collection_id=kr.source_collection_id,
            )
            for i, kr in enumerate(entity.kanji_readings)
        ],
        readings=[
            PracticeEntryReadingORM(
                id=r.id,
                position=i,
                text=r.text,
                no_kanji=r.no_kanji,
                info=r.info,
                restricted_to=r.restricted_to,
                enabled=r.enabled,
                origin=r.origin,
                original_id=r.original_id,
                source_id=r.source_id,
                edited_id=r.edited_id,
                source_collection_id=r.source_collection_id,
            )
            for i, r in enumerate(entity.readings)
        ],
        senses=[_sense_to_db(s, i) for i, s in enumerate(entity.senses)],
        jlpt=entity.jlpt,
        is_common=entity.is_common,
        is_active=entity.is_active,
        notes=entity.notes,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _sense_to_db(entity: PracticeSense, position: int) -> PracticeSenseORM:
    return PracticeSenseORM(
        id=entity.id,
        position=position,
        notes=entity.notes,
        pos=entity.pos,
        misc=entity.misc,
        dialects=entity.dialects,
        info=entity.info,
        enabled=entity.enabled,
        origin=entity.origin,
        original_id=entity.original_id,
        source_id=entity.source_id,
        glosses=[
            PracticeGlossORM(
                id=g.id,
                position=i,
                text=g.text,
                lang=g.lang,
                type=g.type,
                enabled=g.enabled,
                origin=g.origin,
                original_id=g.original_id,
                source_id=g.source_id,
                edited_id=g.edited_id,
                source_collection_id=g.source_collection_id,
            )
            for i, g in enumerate(entity.glosses)
        ],
        examples=[
            PracticeExampleORM(
                id=ex.id,
                position=i,
                text=ex.text,
                sentences=[
                    PracticeExampleSentenceORM(position=j, lang=s.lang, text=s.text)
                    for j, s in enumerate(ex.sentences)
                ],
                enabled=ex.enabled,
                origin=ex.origin,
                original_id=ex.original_id,
                source_id=ex.source_id,
                edited_id=ex.edited_id,
                source_collection_id=ex.source_collection_id,
            )
            for i, ex in enumerate(entity.examples)
        ],
    )
