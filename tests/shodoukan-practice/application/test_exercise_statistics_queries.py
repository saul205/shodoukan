from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from factories import (
    answered,
    make_answered_session,
    make_entry_exercise,
    make_kanji,
    make_kanji_exercise,
    make_word,
)
from sqlalchemy.orm import Session

from shodoukan_practice.application.queries import (
    GetExerciseStatistics,
    GetPracticeStatistics,
)
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyExerciseRepository,
    SqlAlchemyExerciseSessionRepository,
    SqlAlchemyExerciseStatisticsRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)

MADRID = ZoneInfo("Europe/Madrid")


def _exercise_statistics(session: Session) -> GetExerciseStatistics:
    return GetExerciseStatistics(
        SqlAlchemyExerciseRepository(session),
        SqlAlchemyExerciseStatisticsRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def _practice_statistics(session: Session) -> GetPracticeStatistics:
    return GetPracticeStatistics(
        SqlAlchemyExerciseStatisticsRepository(session),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyPracticeKanjiRepository(session),
    )


def test_exercise_statistics_name_missed_words_as_they_are_now(
    session: Session, user: UserORM
) -> None:
    exercise = SqlAlchemyExerciseRepository(session).add(make_entry_exercise(user.id))
    entries = SqlAlchemyPracticeEntryRepository(session)
    eat = entries.add(make_word(user.id, 1, "食べる", "たべる", [("to eat", "eng")]))
    sushi = entries.add(make_word(user.id, 2, None, "すし", [("sushi", "eng")]))
    gone = entries.add(make_word(user.id, 3, "水", "みず", [("water", "eng")]))
    at = datetime(2026, 3, 1, 12, tzinfo=UTC)
    SqlAlchemyExerciseSessionRepository(session).add(
        make_answered_session(
            user.id,
            exercise.id,
            [
                answered(eat.id, False, at, ("writing",), "meaning"),
                answered(sushi.id, False, at, ("meaning",), "writing"),
                answered(sushi.id, False, at, ("meaning",), "writing"),
                answered(gone.id, False, at, ("writing",), "meaning"),
            ],
            item_kind="entries",
            finished_at=at,
        )
    )
    entries.delete(gone)
    assert exercise.id is not None

    statistics = _exercise_statistics(session).execute(user.id, exercise.id)

    assert statistics.totals.answered == 4
    assert [(i.label, i.reading, i.wrong) for i in statistics.most_missed] == [
        ("すし", None, 2),
        ("食べる", "たべる", 1),
    ]
    assert {d.answer_field for d in statistics.directions} == {"meaning", "writing"}


def test_exercise_statistics_of_a_foreign_exercise_is_not_found(
    session: Session, user: UserORM, other_user: UserORM
) -> None:
    exercise = SqlAlchemyExerciseRepository(session).add(make_kanji_exercise(user.id))
    assert exercise.id is not None

    with pytest.raises(EntityNotFoundError):
        _exercise_statistics(session).execute(other_user.id, exercise.id)


def test_activity_counts_answers_per_day_in_the_users_time_zone(
    session: Session, user: UserORM
) -> None:
    kanji = SqlAlchemyPracticeKanjiRepository(session).add(make_kanji(user.id))
    # 23:30 UTC on March 1st is already March 2nd in Madrid (UTC+1).
    SqlAlchemyExerciseSessionRepository(session).add(
        make_answered_session(
            user.id,
            None,
            [
                answered(kanji.id, True, datetime(2026, 3, 1, 10, tzinfo=UTC)),
                answered(kanji.id, False, datetime(2026, 3, 1, 23, 30, tzinfo=UTC)),
                answered(kanji.id, True, datetime(2026, 3, 3, 9, tzinfo=UTC)),
            ],
            finished_at=datetime(2026, 3, 3, 9, tzinfo=UTC),
        )
    )
    now = datetime(2026, 3, 3, 12, tzinfo=UTC)

    statistics = _practice_statistics(session).execute(user.id, now, 3, MADRID)

    assert [(d.day, d.answered, d.correct) for d in statistics.activity] == [
        (date(2026, 3, 1), 1, 1),
        (date(2026, 3, 2), 1, 0),
        (date(2026, 3, 3), 1, 1),
    ]
    assert [(i.label, i.wrong) for i in statistics.most_missed_kanji] == [("食", 1)]
    assert statistics.most_missed_entries == []
    assert statistics.exercises == []  # its exercise was deleted


def test_activity_window_is_bounded(session: Session, user: UserORM) -> None:
    with pytest.raises(ValueError):
        _practice_statistics(session).execute(user.id, datetime.now(UTC), 0, MADRID)
