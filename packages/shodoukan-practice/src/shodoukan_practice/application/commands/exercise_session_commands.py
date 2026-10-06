"""Use cases that run an exercise: start a session, answer its active question
(which asks the next one) and finish it.

The server builds and grades the questions, so statistics don't depend on
the client. Each new question is built from the session's history, so items
aren't repeated before the round is done and missed ones come back. A
handwriting question needs the dictionary: which kanji have a stroke order,
and their strokes, against which the drawing is graded here before the
session records it. None of them commit; the caller owns the transaction.
"""

from random import Random
from uuid import UUID

from ...domain.clock import utc_now
from ...domain.entities import (
    CardSettings,
    ChoiceCardSettings,
    Exercise,
    ExerciseAnswer,
    ExerciseQuestion,
    ExerciseSession,
    HandwritingCardSettings,
    HandwritingGrade,
    HandwritingQuestion,
    StrokesAnswer,
)
from ...domain.exceptions import (
    EntityNotFoundError,
    ExercisePoolTooSmallError,
)
from ...domain.gateways import DictionaryGateway
from ...domain.repositories import (
    EntryCollectionRepository,
    ExerciseRepository,
    ExerciseSessionRepository,
    KanjiCollectionRepository,
    PracticeEntryRepository,
    PracticeKanjiRepository,
    UserRepository,
)
from ...domain.services import (
    StudyCard,
    build_next_question,
    draft_next_question,
    ensure_enough_drawable_items,
    ensure_enough_items,
    entry_card,
    grade_drawing,
    kanji_card,
    kanji_literal,
)
from .collection_lookups import entry_collection, kanji_collection


class _Pool:
    """Reads an exercise's pool: the active items of its collections, as study
    cards in a meaning language."""

    def __init__(
        self,
        entry_collections: EntryCollectionRepository,
        kanji_collections: KanjiCollectionRepository,
        entries: PracticeEntryRepository,
        kanji: PracticeKanjiRepository,
    ) -> None:
        self._entry_collections = entry_collections
        self._kanji_collections = kanji_collections
        self._entries = entries
        self._kanji = kanji

    def cards(self, exercise: Exercise, meaning_lang: str) -> list[StudyCard]:
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


class _Questions:
    """Builds the next question of a session by its exercise's type."""

    def __init__(self, dictionary: DictionaryGateway, rng: Random) -> None:
        self._dictionary = dictionary
        self._rng = rng

    def ensure_enough(self, cards: list[StudyCard], settings: CardSettings) -> None:
        """Raises `ExercisePoolTooSmallError` if the pool can't run a session."""
        if isinstance(settings, HandwritingCardSettings):
            ensure_enough_drawable_items(cards, settings, self._drawable(cards))
        else:
            ensure_enough_items(cards, settings)

    def next(
        self,
        cards: list[StudyCard],
        settings: CardSettings,
        history: list[ExerciseQuestion],
    ) -> ExerciseQuestion:
        """The next question. Raises `ExercisePoolTooSmallError` if the pool
        can't make one."""
        if isinstance(settings, HandwritingCardSettings):
            draft = draft_next_question(
                cards, settings, history, self._drawable(cards), self._rng
            )
            references = self._dictionary.stroke_references(draft.accepted)
            return draft.question(len(history), references)
        assert isinstance(settings, ChoiceCardSettings)
        return build_next_question(cards, settings, history, self._rng)

    def _drawable(self, cards: list[StudyCard]) -> frozenset[str]:
        return self._dictionary.literals_with_strokes(
            text for card in cards if (text := kanji_literal(card)) is not None
        )


def _grade(
    session: ExerciseSession, question_id: int, answer: ExerciseAnswer
) -> HandwritingGrade | None:
    """A drawing's grade, against the active question's kanji. Anything else
    (or a drawing for another question) is checked by the session."""
    current = session.current
    if (
        isinstance(answer, StrokesAnswer)
        and isinstance(current, HandwritingQuestion)
        and current.id == question_id
    ):
        return grade_drawing(answer, current.references)
    return None


def _session_to_change(
    sessions: ExerciseSessionRepository, session_id: int, user_id: UUID
) -> ExerciseSession:
    """The session, locked until the transaction ends so concurrent changes to
    it (a double click) are serialized."""
    session = sessions.get_for_update(session_id, user_id)
    if session is None:
        raise EntityNotFoundError(f"exercise session {session_id} not found")
    return session


class StartExerciseSession:
    """Start studying an exercise: a new session with its first question.

    The user's open sessions, of any exercise, are closed at their last
    activity: a user studies one session at a time. `meaning_lang` is the language
    meanings are shown and compared in, as the items store it (`eng` for entry
    glosses, `en` for kanji meanings). Raises `EntityNotFoundError` for an
    unknown exercise and `ExercisePoolTooSmallError` if its collections don't
    have enough usable items.
    """

    def __init__(
        self,
        exercises: ExerciseRepository,
        sessions: ExerciseSessionRepository,
        entry_collections: EntryCollectionRepository,
        kanji_collections: KanjiCollectionRepository,
        entries: PracticeEntryRepository,
        kanji: PracticeKanjiRepository,
        dictionary: DictionaryGateway,
        users: UserRepository,
        rng: Random | None = None,
    ) -> None:
        self._exercises = exercises
        self._sessions = sessions
        self._users = users
        self._pool = _Pool(entry_collections, kanji_collections, entries, kanji)
        self._questions = _Questions(dictionary, rng or Random())

    def execute(
        self, user_id: UUID, exercise_id: int, meaning_lang: str
    ) -> ExerciseSession:
        exercise = self._exercises.get(exercise_id, user_id)
        if exercise is None:
            raise EntityNotFoundError(f"exercise {exercise_id} not found")
        cards = self._pool.cards(exercise, meaning_lang)
        self._questions.ensure_enough(cards, exercise.settings)
        first = self._questions.next(cards, exercise.settings, [])

        # One open session per user: lock the user so concurrent starts take
        # turns, then close the open ones (locked too, so an answer being
        # stored in another tab finishes first).
        self._users.lock(user_id)
        for previous in self._sessions.list_open(user_id):
            previous.close_at_last_activity()
            self._sessions.update(previous)

        session = ExerciseSession(
            id=None,
            user_id=user_id,
            exercise_id=exercise_id,
            exercise_name=exercise.name,
            item_kind=exercise.item_kind,
            meaning_lang=meaning_lang,
        )
        session.ask(first)
        return self._sessions.add(session)


class AnswerExerciseQuestion:
    """Grade the session's active question and ask the next one.

    Returns the session, the graded question (with its solution) and the next
    active question. The next one is None if the pool can't make another (the
    session stays open; the user can finish it), or if the exercise was
    deleted (the session is finished; the answer still counts). An idle
    session refuses the answer and isn't written: it's closed for good when
    it's finished or the exercise is started again.
    Raises `EntityNotFoundError`, `SessionFinishedError`,
    `QuestionNotActiveError` or `InvalidAnswerError`.
    """

    def __init__(
        self,
        exercises: ExerciseRepository,
        sessions: ExerciseSessionRepository,
        entry_collections: EntryCollectionRepository,
        kanji_collections: KanjiCollectionRepository,
        entries: PracticeEntryRepository,
        kanji: PracticeKanjiRepository,
        dictionary: DictionaryGateway,
        rng: Random | None = None,
    ) -> None:
        self._exercises = exercises
        self._sessions = sessions
        self._pool = _Pool(entry_collections, kanji_collections, entries, kanji)
        self._questions = _Questions(dictionary, rng or Random())

    def execute(
        self,
        user_id: UUID,
        session_id: int,
        question_id: int,
        answer: ExerciseAnswer,
        response_ms: int | None = None,
    ) -> tuple[ExerciseSession, ExerciseQuestion, ExerciseQuestion | None]:
        session = _session_to_change(self._sessions, session_id, user_id)
        grade = _grade(session, question_id, answer)
        session.answer(question_id, answer, response_ms, grade)
        self._ask_next(session)
        stored = self._sessions.update(session)
        return stored, stored.history[-1], stored.current

    def _ask_next(self, session: ExerciseSession) -> None:
        """Ask the next question, if the exercise can still make one."""
        exercise = (
            self._exercises.get(session.exercise_id, session.user_id)
            if session.exercise_id is not None
            else None
        )
        if exercise is None:
            session.finish()  # the exercise was deleted: nothing more to ask
            return
        cards = self._pool.cards(exercise, session.meaning_lang)
        try:
            question = self._questions.next(cards, exercise.settings, session.history)
        except ExercisePoolTooSmallError:
            return
        session.ask(question)


class FinishExerciseSession:
    """Close a session; its active question, never answered, is dropped.

    Finishing a finished session changes nothing. Raises
    `EntityNotFoundError`.
    """

    def __init__(self, sessions: ExerciseSessionRepository) -> None:
        self._sessions = sessions

    def execute(self, user_id: UUID, session_id: int) -> ExerciseSession:
        session = _session_to_change(self._sessions, session_id, user_id)
        if session.is_finished:
            return session
        if not session.close_if_idle(utc_now()):
            session.finish()
        return self._sessions.update(session)
