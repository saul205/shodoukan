import pytest
from factories import TIMESTAMPS
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shodoukan_practice.infrastructure.db.orm import (
    PracticeKanjiMeaningORM,
    PracticeKanjiORM,
    PracticeKanjiReadingItemORM,
    UserORM,
)


def make_kanji(user: UserORM, literal: str = "食") -> PracticeKanjiORM:
    return PracticeKanjiORM(
        **TIMESTAMPS,
        user_id=user.id,
        literal=literal,
        grade=2,
        stroke_count=9,
        freq=316,
        jlpt=4,
        reading_items=[
            PracticeKanjiReadingItemORM(kind="on", position=0, text="ショク"),
            PracticeKanjiReadingItemORM(kind="kun", position=0, text="た.べる"),
        ],
        meanings=[PracticeKanjiMeaningORM(position=0, text="eat", lang="en")],
    )


def test_reading_items_keep_their_kind(session: Session, user: UserORM) -> None:
    session.add(make_kanji(user))
    session.commit()
    session.expunge_all()

    kanji = session.scalars(select(PracticeKanjiORM)).one()
    by_kind = {item.kind: item.text for item in kanji.reading_items}
    assert by_kind == {"on": "ショク", "kun": "た.べる"}


def test_reading_kind_is_checked(session: Session, user: UserORM) -> None:
    kanji = make_kanji(user)
    kanji.reading_items[0].kind = "onyomi"
    session.add(kanji)
    with pytest.raises(IntegrityError):
        session.commit()


def test_literal_is_unique_per_user(session: Session, user: UserORM) -> None:
    session.add_all([make_kanji(user), make_kanji(user)])
    with pytest.raises(IntegrityError):
        session.commit()


def test_same_literal_for_different_users(session: Session, user: UserORM) -> None:
    other = UserORM(subject="sub-other", username="other", **TIMESTAMPS)
    session.add(other)
    session.flush()
    session.add_all([make_kanji(user), make_kanji(other)])
    session.commit()
