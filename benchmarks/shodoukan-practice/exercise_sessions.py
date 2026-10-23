"""Benchmark exercise sessions on real dictionary data.

Imports words and kanji from the downloaded dictionary into a practice
database in memory (SQLite), through the real use cases, then times starting
a session and answering its questions for each kind of exercise. It isn't a
test: it prints timings, to run whenever a change may affect how sessions
load their pool.

    python benchmarks/shodoukan-practice/exercise_sessions.py
    python benchmarks/shodoukan-practice/exercise_sessions.py --entries 50 --answers 5

Needs the dictionary database (`shodoukan-setup`).
"""

import argparse
import sqlite3
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from shodoukan import Dictionary
from shodoukan.db.connection import resolve_path
from shodoukan_practice.application.commands import (
    AnswerExerciseQuestion,
    CreateEntryCollection,
    CreateExercise,
    CreateKanjiCollection,
    ImportEntry,
    ImportKanji,
    StartExerciseSession,
)
from shodoukan_practice.domain.clock import utc_now
from shodoukan_practice.domain.entities import (
    ChoiceCardSettings,
    ChoiceQuestion,
    ExerciseAnswer,
    ExerciseQuestion,
    ExerciseSettings,
    HandwritingCardSettings,
    ItemKind,
    OptionAnswer,
    SkipAnswer,
)
from shodoukan_practice.domain.gateways import DictionaryGateway
from shodoukan_practice.infrastructure.db.orm import (
    Base,
    PracticeEntryORM,
    PracticeGlossORM,
    PracticeKanjiORM,
    PracticeSenseORM,
    UserORM,
)
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
    SqlAlchemyUserRepository,
)


def _choice(*directions: tuple[str, str]) -> ChoiceCardSettings:
    return ChoiceCardSettings.model_validate(
        {"directions": [{"prompt": [p], "answer": a} for p, a in directions]}
    )


# (name, item kind, meaning language as the items store it, settings)
SCENARIOS: list[tuple[str, ItemKind, str, ExerciseSettings]] = [
    (
        "words, choice",
        "entries",
        "eng",
        _choice(("meaning", "writing"), ("writing", "meaning")),
    ),
    (
        "kanji, choice",
        "kanji",
        "en",
        _choice(("literal", "meaning"), ("meaning", "literal")),
    ),
    (
        "kanji, handwriting",
        "kanji",
        "en",
        HandwritingCardSettings.model_validate(
            {"directions": [{"prompt": ["meaning"], "answer": "literal"}]}
        ),
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark exercise sessions.")
    parser.add_argument("--entries", type=int, default=1000, help="words to import")
    parser.add_argument("--kanji", type=int, default=500, help="kanji to import")
    parser.add_argument("--answers", type=int, default=20, help="answers per session")
    args = parser.parse_args()

    path = resolve_path()
    if not path.exists():
        sys.exit(f"No dictionary database at {path}: run `shodoukan-setup` first.")
    gateway = ShodoukanDictionaryGateway(Dictionary(path, auto_download=False))
    engine = _practice_engine()
    user_id = uuid4()

    with Session(engine) as session:
        now = utc_now()
        session.add(
            UserORM(id=user_id, username="bench", created_at=now, updated_at=now)
        )
        started = time.perf_counter()
        _seed(session, gateway, user_id, path, args.entries, args.kanji)
        session.commit()
        seconds = time.perf_counter() - started
        print(f"Seeded in {seconds:.1f} s: {_counts(session)}\n")

    print(f"{'scenario':<20} {'pool':>8} {'start':>8} {'answer':>8} {'max':>8}  (ms)")
    for name, kind, lang, settings in SCENARIOS:
        pool, start, answers = _run(
            engine, gateway, user_id, kind, lang, settings, args.answers
        )
        print(
            f"{name:<20} {pool:8.1f} {start:8.1f} "
            f"{statistics.median(answers):8.1f} {max(answers):8.1f}"
        )
    print(
        f"\npool: reading it alone; start: a new session and its first question; "
        f"answer: median of {args.answers} answers, each asking the next question"
    )


def _practice_engine() -> Engine:
    """SQLite in memory, set up as the tests do (foreign keys, savepoints)."""
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def _configure(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys = ON")
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _begin(connection: Any) -> None:
        connection.exec_driver_sql("BEGIN")

    Base.metadata.create_all(engine)
    return engine


def _seed(
    session: Session,
    gateway: DictionaryGateway,
    user_id: UUID,
    path: Path,
    entries: int,
    kanji: int,
) -> None:
    """Common words by id, and the most frequent kanji with a stroke order,
    each kind in a collection of its own."""
    with sqlite3.connect(path) as dictionary:
        entry_ids = [
            row[0]
            for row in dictionary.execute(
                "SELECT id FROM entries WHERE has_common = 1 ORDER BY id LIMIT ?",
                (entries,),
            )
        ]
        literals = [
            row[0]
            for row in dictionary.execute(
                "SELECT k.literal FROM kanji k JOIN kanji_svg s USING (literal)"
                " ORDER BY k.freq IS NULL, k.freq, k.literal LIMIT ?",
                (kanji,),
            )
        ]
    entry_collections = SqlAlchemyEntryCollectionRepository(session)
    kanji_collections = SqlAlchemyKanjiCollectionRepository(session)
    words = CreateEntryCollection(entry_collections).execute(user_id, "words")
    characters = CreateKanjiCollection(kanji_collections).execute(user_id, "kanji")
    assert words.id is not None and characters.id is not None
    import_entry = ImportEntry(
        gateway, SqlAlchemyPracticeEntryRepository(session), entry_collections
    )
    for entry_id in entry_ids:
        import_entry.execute(user_id, entry_id, [words.id])
    import_kanji = ImportKanji(
        gateway, SqlAlchemyPracticeKanjiRepository(session), kanji_collections
    )
    for literal in literals:
        import_kanji.execute(user_id, literal, [characters.id])


def _counts(session: Session) -> str:
    tables = {
        "words": PracticeEntryORM,
        "senses": PracticeSenseORM,
        "glosses": PracticeGlossORM,
        "kanji": PracticeKanjiORM,
    }
    return ", ".join(
        f"{session.scalar(select(func.count()).select_from(orm))} {name}"
        for name, orm in tables.items()
    )


def _run(
    engine: Engine,
    gateway: DictionaryGateway,
    user_id: UUID,
    kind: ItemKind,
    lang: str,
    settings: ExerciseSettings,
    answer_count: int,
) -> tuple[float, float, list[float]]:
    """Times, in ms: reading the pool alone, starting a session and each
    answer. Every step commits, as a request does."""
    with Session(engine) as session:
        exercises = SqlAlchemyExerciseRepository(session)
        entry_collections = SqlAlchemyEntryCollectionRepository(session)
        kanji_collections = SqlAlchemyKanjiCollectionRepository(session)
        entries = SqlAlchemyPracticeEntryRepository(session)
        kanji = SqlAlchemyPracticeKanjiRepository(session)
        repos = (
            exercises,
            SqlAlchemyExerciseSessionRepository(session),
            entry_collections,
            kanji_collections,
            entries,
            kanji,
            gateway,
        )

        started = time.perf_counter()
        if kind == "entries":
            (words,) = entry_collections.list_for_user(user_id)
            entries.study_texts(entry_collections.item_ids([words]), user_id, lang)
            collection_id = words.id
        else:
            (characters,) = kanji_collections.list_for_user(user_id)
            kanji.study_texts(kanji_collections.item_ids([characters]), user_id, lang)
            collection_id = characters.id
        pool = time.perf_counter() - started

        assert collection_id is not None
        exercise = CreateExercise(exercises, entry_collections, kanji_collections)
        exercise_id = exercise.execute(
            user_id, kind, kind, None, [collection_id], settings
        ).id
        session.commit()
        assert exercise_id is not None

        started = time.perf_counter()
        exercise_session = StartExerciseSession(
            *repos, SqlAlchemyUserRepository(session)
        ).execute(user_id, exercise_id, lang)
        session.commit()
        start = time.perf_counter() - started

        answer = AnswerExerciseQuestion(*repos)
        current = exercise_session.current
        answers: list[float] = []
        while current is not None and len(answers) < answer_count:
            assert exercise_session.id is not None and current.id is not None
            started = time.perf_counter()
            _, _, current = answer.execute(
                user_id, exercise_session.id, current.id, _answer_to(current)
            )
            session.commit()
            answers.append((time.perf_counter() - started) * 1000)
    return pool * 1000, start * 1000, answers


def _answer_to(question: ExerciseQuestion) -> ExerciseAnswer:
    """A choice question's first option. A drawing is skipped: grading one
    would time the grader, not how the session loads its pool."""
    if isinstance(question, ChoiceQuestion):
        return OptionAnswer(option=0)
    return SkipAnswer()


if __name__ == "__main__":
    main()
