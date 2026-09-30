import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shodoukan_practice.infrastructure.db.orm import (
    PracticeEntryORM,
    PracticeEntryReadingORM,
    PracticeExampleORM,
    PracticeExampleSentenceORM,
    PracticeGlossORM,
    PracticeSenseORM,
    UserORM,
)


def make_entry(user: UserORM, source_entry_id: int = 1000001) -> PracticeEntryORM:
    return PracticeEntryORM(
        user_id=user.id,
        source_entry_id=source_entry_id,
        jlpt=5,
        is_common=True,
        readings=[
            PracticeEntryReadingORM(
                position=1, text="たべる", no_kanji=False, info=[], restricted_to=[]
            ),
            PracticeEntryReadingORM(
                position=0, text="くう", no_kanji=False, info=[], restricted_to=[]
            ),
        ],
        senses=[
            PracticeSenseORM(
                position=0,
                pos=["v1"],
                misc=[],
                dialects=[],
                info=[],
                glosses=[
                    PracticeGlossORM(position=0, text="to eat", lang="eng"),
                ],
                examples=[
                    PracticeExampleORM(
                        position=0,
                        text="",
                        sentences=[
                            PracticeExampleSentenceORM(
                                position=0, lang="jpn", text="ご飯を食べる。"
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def count(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_children_load_in_position_order(session: Session, user: UserORM) -> None:
    session.add(make_entry(user))
    session.commit()
    session.expunge_all()

    entry = session.scalars(select(PracticeEntryORM)).one()
    assert [r.text for r in entry.readings] == ["くう", "たべる"]


def test_python_side_defaults(session: Session, user: UserORM) -> None:
    session.add(make_entry(user))
    session.commit()

    gloss = session.scalars(select(PracticeGlossORM)).one()
    entry = session.scalars(select(PracticeEntryORM)).one()
    assert gloss.enabled is True
    assert gloss.origin == "imported"
    assert entry.is_active is True
    assert entry.senses[0].pos == ["v1"]


def test_deleting_entry_cascades_to_nested_rows(
    session: Session, user: UserORM
) -> None:
    session.add(make_entry(user))
    session.commit()

    session.delete(session.scalars(select(PracticeEntryORM)).one())
    session.commit()

    for model in (
        PracticeEntryReadingORM,
        PracticeSenseORM,
        PracticeGlossORM,
        PracticeExampleORM,
        PracticeExampleSentenceORM,
    ):
        assert count(session, model) == 0


def test_source_entry_is_unique_per_user(session: Session, user: UserORM) -> None:
    session.add(make_entry(user))
    session.add(make_entry(user))
    with pytest.raises(IntegrityError):
        session.commit()


def test_gloss_origin_is_checked(session: Session, user: UserORM) -> None:
    entry = make_entry(user)
    entry.senses[0].glosses[0].origin = "invented"
    session.add(entry)
    with pytest.raises(IntegrityError):
        session.commit()
