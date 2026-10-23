"""Exercise <-> exercises and its collection link table.

The subclass picks the link table (entry or kanji collections); list order is
stored as `position`. `settings` goes through JSON-compatible dicts.
"""

from pydantic import TypeAdapter

from ....domain.entities import (
    EntryExercise,
    Exercise,
    ExerciseSettings,
    KanjiExercise,
)
from ..orm import ExerciseEntryCollectionORM, ExerciseKanjiCollectionORM, ExerciseORM

_settings = TypeAdapter[ExerciseSettings](ExerciseSettings)


def exercise_to_domain(row: ExerciseORM) -> Exercise:
    exercise_class: type[Exercise]
    links: list[ExerciseEntryCollectionORM] | list[ExerciseKanjiCollectionORM]
    if row.item_kind == "entries":
        exercise_class, links = EntryExercise, row.entry_collections
    elif row.item_kind == "kanji":
        exercise_class, links = KanjiExercise, row.kanji_collections
    else:
        raise ValueError(f"unknown exercise item kind {row.item_kind!r}")
    return exercise_class(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        description=row.description,
        collection_ids=tuple(link.collection_id for link in links),
        settings=_settings.validate_python(row.settings),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def exercise_to_db(entity: Exercise) -> ExerciseORM:
    row = ExerciseORM(
        id=entity.id,
        user_id=entity.user_id,
        name=entity.name,
        description=entity.description,
        item_kind=entity.item_kind,
        settings=_settings.dump_python(entity.settings, mode="json"),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
    if isinstance(entity, EntryExercise):
        row.entry_collections = [
            ExerciseEntryCollectionORM(
                exercise_id=entity.id, collection_id=collection_id, position=position
            )
            for position, collection_id in enumerate(entity.collection_ids)
        ]
    else:
        row.kanji_collections = [
            ExerciseKanjiCollectionORM(
                exercise_id=entity.id, collection_id=collection_id, position=position
            )
            for position, collection_id in enumerate(entity.collection_ids)
        ]
    return row
