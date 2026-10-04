"""PracticeKanji <-> practice_kanji and its nested tables.

On-readings, kun-readings and nanori share one table, told apart by `kind`.
List order in the domain is stored as `position` (index within its kind).
"""

from typing import Literal

from ....domain.entities import (
    PracticeKanji,
    PracticeKanjiMeaning,
    PracticeReadingItem,
)
from ..orm import PracticeKanjiMeaningORM, PracticeKanjiORM, PracticeKanjiReadingItemORM


def _origin(value: str) -> Literal["imported", "added"]:
    if value == "imported":
        return "imported"
    if value == "added":
        return "added"
    raise ValueError(f"unknown origin {value!r}")


def _items(row: PracticeKanjiORM, kind: str) -> list[PracticeReadingItem]:
    return [
        PracticeReadingItem(id=item.id, text=item.text, enabled=item.enabled)
        for item in row.reading_items
        if item.kind == kind
    ]


def practice_kanji_to_domain(row: PracticeKanjiORM) -> PracticeKanji:
    return PracticeKanji(
        id=row.id,
        user_id=row.user_id,
        literal=row.literal,
        grade=row.grade,
        stroke_count=row.stroke_count,
        freq=row.freq,
        jlpt=row.jlpt,
        on_readings=_items(row, "on"),
        kun_readings=_items(row, "kun"),
        nanori=_items(row, "nanori"),
        meanings=[
            PracticeKanjiMeaning(
                id=m.id,
                text=m.text,
                lang=m.lang,
                enabled=m.enabled,
                origin=_origin(m.origin),
            )
            for m in row.meanings
        ],
        is_active=row.is_active,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def practice_kanji_to_db(entity: PracticeKanji) -> PracticeKanjiORM:
    by_kind = {
        "on": entity.on_readings,
        "kun": entity.kun_readings,
        "nanori": entity.nanori,
    }
    return PracticeKanjiORM(
        id=entity.id,
        user_id=entity.user_id,
        literal=entity.literal,
        grade=entity.grade,
        stroke_count=entity.stroke_count,
        freq=entity.freq,
        jlpt=entity.jlpt,
        reading_items=[
            PracticeKanjiReadingItemORM(
                id=item.id, kind=kind, position=i, text=item.text, enabled=item.enabled
            )
            for kind, items in by_kind.items()
            for i, item in enumerate(items)
        ],
        meanings=[
            PracticeKanjiMeaningORM(
                id=m.id,
                position=i,
                text=m.text,
                lang=m.lang,
                enabled=m.enabled,
                origin=m.origin,
            )
            for i, m in enumerate(entity.meanings)
        ],
        is_active=entity.is_active,
        notes=entity.notes,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
