from datetime import datetime, timedelta

import pytest
from factories import (
    NOW,
    answered,
    make_answered_session,
    make_kanji,
    make_kanji_exercise,
    make_word,
)
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import Exercise
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyExerciseStatisticsRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyExerciseStatisticsRepository:
    return SqlAlchemyExerciseStatisticsRepository(session)


@pytest.fixture
def sessions(session: Session) -> SqlAlchemyExerciseSessionRepository:
    return SqlAlchemyExerciseSessionRepository(session)


@pytest.fixture
def exercises(session: Session, user: UserORM) -> tuple[Exercise, Exercise]:
    repo = SqlAlchemyExerciseRepository(session)
    return (
        repo.add(make_kanji_exercise(user.id, name="N5")),
        repo.add(make_kanji_exercise(user.id, name="N4")),
    )


@pytest.fixture
def kanji_ids(session: Session, user: UserORM) -> list[int]:
    repo = SqlAlchemyPracticeKanjiRepository(session)
    return [repo.add(make_kanji(user.id, literal)).id or 0 for literal in "食水火"]


def at(minutes: int) -> datetime:
    return NOW + timedelta(minutes=minutes)


def test_totals_over_all_or_one_exercise(
    repo: SqlAlchemyExerciseStatisticsRepository,
    sessions: SqlAlchemyExerciseSessionRepository,
    exercises: tuple[Exercise, Exercise],
    kanji_ids: list[int],
    user: UserORM,
    other_user: UserORM,
) -> None:
    n5, n4 = exercises
    a, b, _ = kanji_ids
    sessions.add(
        make_answered_session(
            user.id,
            n5.id,
            [answered(a, True, at(0)), answered(b, False, at(1))],
            finished_at=at(2),
            response_ms=1000,
        )
    )
    sessions.add(
        make_answered_session(
            user.id,
            n4.id,
            [answered(a, True, at(10))],
            finished_at=at(11),
            response_ms=4000,
        )
    )
    sessions.add(make_answered_session(user.id, n5.id, [], finished_at=at(20)))

    overall = repo.totals(user.id)
    assert (overall.sessions, overall.answered, overall.correct) == (2, 3, 2)
    assert overall.mean_response_ms == pytest.approx(2000)
    of_n5 = repo.totals(user.id, n5)
    assert (of_n5.sessions, of_n5.answered, of_n5.correct) == (1, 2, 1)
    nothing = repo.totals(other_user.id)
    assert (nothing.answered, nothing.correct, nothing.mean_response_ms) == (0, 0, None)


def test_by_direction_treats_the_shown_fields_as_a_set(
    repo: SqlAlchemyExerciseStatisticsRepository,
    sessions: SqlAlchemyExerciseSessionRepository,
    exercises: tuple[Exercise, Exercise],
    user: UserORM,
) -> None:
    n5, _ = exercises
    sessions.add(
        make_answered_session(
            user.id,
            n5.id,
            [
                answered(None, True, at(0), ("literal", "meaning"), "kunyomi"),
                answered(None, False, at(1), ("meaning", "literal"), "kunyomi"),
                answered(None, True, at(2), ("literal",), "onyomi"),
            ],
            finished_at=at(3),
        )
    )

    rows = repo.by_direction(user.id, n5)

    assert [
        (set(r.prompt_fields), r.answer_field, r.answered, r.correct) for r in rows
    ] == [
        ({"literal", "meaning"}, "kunyomi", 2, 1),
        ({"literal"}, "onyomi", 1, 1),
    ]


def test_most_missed_by_kind_skips_removed_items(
    session: Session,
    repo: SqlAlchemyExerciseStatisticsRepository,
    sessions: SqlAlchemyExerciseSessionRepository,
    exercises: tuple[Exercise, Exercise],
    kanji_ids: list[int],
    user: UserORM,
) -> None:
    n5, _ = exercises
    a, b, c = kanji_ids
    sessions.add(
        make_answered_session(
            user.id,
            n5.id,
            [
                answered(a, False, at(0)),
                answered(b, False, at(1)),
                answered(b, False, at(2)),
                answered(a, True, at(3)),
                answered(c, True, at(4)),  # never missed
                answered(None, False, at(5)),  # left the library
            ],
            finished_at=at(6),
        )
    )
    word = SqlAlchemyPracticeEntryRepository(session).add(
        make_word(user.id, 1000, "食べる", "たべる", [("to eat", "eng")])
    )
    sessions.add(
        make_answered_session(
            user.id,
            None,
            [answered(word.id, False, at(7), ("writing",), "meaning")],
            item_kind="entries",
            finished_at=at(8),
        )
    )

    kanji = repo.most_missed_kanji(user.id)
    assert [(k.item_id, k.answered, k.wrong) for k in kanji] == [(b, 2, 2), (a, 2, 1)]
    assert [k.item_id for k in repo.most_missed_kanji(user.id, limit=1)] == [b]
    entries = repo.most_missed_entries(user.id)
    assert [(e.item_id, e.wrong) for e in entries] == [(word.id, 1)]
    assert repo.most_missed_entries(user.id, n5) == []


def test_by_exercise_uses_the_current_name_and_skips_deleted_ones(
    session: Session,
    repo: SqlAlchemyExerciseStatisticsRepository,
    sessions: SqlAlchemyExerciseSessionRepository,
    exercises: tuple[Exercise, Exercise],
    user: UserORM,
) -> None:
    n5, n4 = exercises
    sessions.add(
        make_answered_session(
            user.id, n5.id, [answered(None, True, at(0))], finished_at=at(1)
        )
    )
    sessions.add(
        make_answered_session(
            user.id,
            n4.id,
            [answered(None, True, at(10)), answered(None, False, at(11))],
            finished_at=at(12),
        )
    )
    sessions.add(
        make_answered_session(
            user.id, None, [answered(None, True, at(20))], finished_at=at(21)
        )
    )
    n5.rename("N5 renamed")
    SqlAlchemyExerciseRepository(session).update(n5)

    rows = repo.by_exercise(user.id)

    assert [(r.exercise_name, r.sessions, r.answered, r.correct) for r in rows] == [
        ("N4", 1, 2, 1),
        ("N5 renamed", 1, 1, 1),
    ]
    assert rows[0].last_answered_at == at(11)


def test_answers_since(
    repo: SqlAlchemyExerciseStatisticsRepository,
    sessions: SqlAlchemyExerciseSessionRepository,
    exercises: tuple[Exercise, Exercise],
    user: UserORM,
    other_user: UserORM,
) -> None:
    n5, _ = exercises
    sessions.add(
        make_answered_session(
            user.id,
            n5.id,
            [answered(None, True, at(0)), answered(None, False, at(60))],
            finished_at=at(61),
        )
    )

    moments = repo.answers_since(user.id, at(30))

    assert [(m.answered_at, m.is_correct) for m in moments] == [(at(60), False)]
    assert repo.answers_since(other_user.id, at(-60)) == []
