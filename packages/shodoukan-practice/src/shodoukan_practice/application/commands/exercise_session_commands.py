"""Use cases that run an exercise: start a session and answer its questions.

The server builds and grades the questions, so statistics don't depend on
the client. None of them commit; the caller owns the transaction.
"""

from random import Random
from uuid import UUID

from ...domain.entities import (
    Exercise,
    ExerciseAnswer,
    ExerciseQuestion,
    ExerciseSession,
)
from ...domain.exceptions import EntityNotFoundError
from ...domain.repositories import (
    EntryCollectionRepository,
    ExerciseRepository,
    ExerciseSessionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
)
from ...domain.services import (
    StudyCard,
    build_choice_questions,
    entry_card,
    kanji_card,
)
from .collection_lookups import entry_collection, kanji_collection


class StartExerciseSession:
    """Build a session of questions from the exercise's collections.

    Only active items count. `meaning_lang` is the language meanings are
    shown and compared in, as the items store it (`eng` for entry glosses,
    `en` for kanji meanings). Raises `EntityNotFoundError` for an unknown
    exercise and `ExercisePoolTooSmallError` if its collections don't have
    enough usable items.
    """

    def __init__(
        self,
        exercises: ExerciseRepository,
        sessions: ExerciseSessionRepository,
        entry_collections: EntryCollectionRepository,
        kanji_collections: KanjiCollectionRepository,
        entries: PracticeEntryRepository,
        kanji: PracticeKanjiRepository,
        rng: Random | None = None,
    ) -> None:
        self._exercises = exercises
        self._sessions = sessions
        self._entry_collections = entry_collections
        self._kanji_collections = kanji_collections
        self._entries = entries
        self._kanji = kanji
        self._rng = rng or Random()

    def execute(
        self, user_id: UUID, exercise_id: int, meaning_lang: str
    ) -> ExerciseSession:
        exercise = self._exercises.get(exercise_id, user_id)
        if exercise is None:
            raise EntityNotFoundError(f"exercise {exercise_id} not found")
        questions = build_choice_questions(
            self._cards(exercise, meaning_lang), exercise.settings, self._rng
        )
        return self._sessions.add(
            ExerciseSession(
                id=None,
                user_id=user_id,
                exercise_id=exercise.id,
                exercise_name=exercise.name,
                item_kind=exercise.item_kind,
                meaning_lang=meaning_lang,
                questions=questions,
            )
        )

    def _cards(self, exercise: Exercise, meaning_lang: str) -> list[StudyCard]:
        """The pool: the active items of the exercise's collections."""
        user_id, fields = exercise.user_id, exercise.settings.fields
        if exercise.item_kind == "entries":
            entry_collections = [
                entry_collection(self._entry_collections, cid, user_id)
                for cid in exercise.collection_ids
            ]
            ids = self._entry_collections.item_ids(entry_collections)
            return [
                entry_card(entry, fields, meaning_lang)
                for entry in self._entries.get_many(ids, user_id)
            ]
        kanji_collections = [
            kanji_collection(self._kanji_collections, cid, user_id)
            for cid in exercise.collection_ids
        ]
        ids = self._kanji_collections.item_ids(kanji_collections)
        return [
            kanji_card(item, fields, meaning_lang)
            for item in self._kanji.get_many(ids, user_id)
        ]


class AnswerExerciseQuestion:
    """Grade the answer to one question of a session, once.

    Returns the question with its solution. Raises `EntityNotFoundError`,
    `QuestionAnsweredError` or `InvalidAnswerError`.
    """

    def __init__(self, sessions: ExerciseSessionRepository) -> None:
        self._sessions = sessions

    def execute(
        self,
        user_id: UUID,
        session_id: int,
        question_id: int,
        answer: ExerciseAnswer,
        response_ms: int | None = None,
    ) -> tuple[ExerciseSession, ExerciseQuestion]:
        session = self._sessions.get(session_id, user_id)
        if session is None:
            raise EntityNotFoundError(f"exercise session {session_id} not found")
        session.answer(question_id, answer, response_ms)
        stored = self._sessions.update(session)
        question = next(q for q in stored.questions if q.id == question_id)
        return stored, question
