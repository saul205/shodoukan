"""Use cases that create, edit and delete a user's saved exercises.

The collections an exercise draws from are looked up by its item kind and
scoped to the user, so another user's collection, or a collection of the
other kind with the same id, is "not found". None of them commit; the caller
owns the transaction.
"""

from collections.abc import Sequence
from uuid import UUID

from ...domain.entities import (
    EntryExercise,
    Exercise,
    ExerciseSettings,
    ItemKind,
    KanjiExercise,
)
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    EntryCollectionRepository,
    ExerciseRepository,
    KanjiCollectionRepository,
)
from .collection_lookups import entry_collection, kanji_collection


def _exercise(
    exercises: ExerciseRepository, exercise_id: int, user_id: UUID
) -> Exercise:
    exercise = exercises.get(exercise_id, user_id)
    if exercise is None:
        raise EntityNotFoundError(f"exercise {exercise_id} not found")
    return exercise


class _CollectionResolver:
    """Checks that each collection id is one of the user's, of the right kind."""

    def __init__(
        self,
        entry_collections: EntryCollectionRepository,
        kanji_collections: KanjiCollectionRepository,
    ) -> None:
        self._entry_collections = entry_collections
        self._kanji_collections = kanji_collections

    def ids(
        self, item_kind: ItemKind, collection_ids: Sequence[int], user_id: UUID
    ) -> tuple[int, ...]:
        """The ids, deduplicated in order. Raises `EntityNotFoundError`."""
        unique = tuple(dict.fromkeys(collection_ids))
        for collection_id in unique:
            if item_kind == "entries":
                entry_collection(self._entry_collections, collection_id, user_id)
            else:
                kanji_collection(self._kanji_collections, collection_id, user_id)
        return unique


class CreateExercise:
    """Save a new exercise over some of the user's collections.

    Raises `EntityNotFoundError` for an unknown collection, and a validation
    error for settings that use fields of the other item kind.
    """

    def __init__(
        self,
        exercises: ExerciseRepository,
        entry_collections: EntryCollectionRepository,
        kanji_collections: KanjiCollectionRepository,
    ) -> None:
        self._exercises = exercises
        self._collections = _CollectionResolver(entry_collections, kanji_collections)

    def execute(
        self,
        user_id: UUID,
        item_kind: ItemKind,
        name: str,
        description: str | None,
        collection_ids: Sequence[int],
        settings: ExerciseSettings,
    ) -> Exercise:
        exercise_class = EntryExercise if item_kind == "entries" else KanjiExercise
        exercise = exercise_class(
            id=None,
            user_id=user_id,
            name=name,
            description=description,
            collection_ids=self._collections.ids(item_kind, collection_ids, user_id),
            settings=settings,
        )
        return self._exercises.add(exercise)


class UpdateExercise:
    """Replace an exercise's name, description, collections and settings.

    Its item kind never changes. Unchanged values leave `updated_at` alone.
    Same errors as `CreateExercise`, plus `EntityNotFoundError` for the
    exercise itself.
    """

    def __init__(
        self,
        exercises: ExerciseRepository,
        entry_collections: EntryCollectionRepository,
        kanji_collections: KanjiCollectionRepository,
    ) -> None:
        self._exercises = exercises
        self._collections = _CollectionResolver(entry_collections, kanji_collections)

    def execute(
        self,
        user_id: UUID,
        exercise_id: int,
        name: str,
        description: str | None,
        collection_ids: Sequence[int],
        settings: ExerciseSettings,
    ) -> Exercise:
        exercise = _exercise(self._exercises, exercise_id, user_id)
        exercise.rename(name)
        exercise.describe(description)
        exercise.use_collections(
            self._collections.ids(exercise.item_kind, collection_ids, user_id)
        )
        exercise.configure(settings)
        return self._exercises.update(exercise)


class DeleteExercise:
    """Delete an exercise. Its collections stay."""

    def __init__(self, exercises: ExerciseRepository) -> None:
        self._exercises = exercises

    def execute(self, user_id: UUID, exercise_id: int) -> None:
        self._exercises.delete(_exercise(self._exercises, exercise_id, user_id))
