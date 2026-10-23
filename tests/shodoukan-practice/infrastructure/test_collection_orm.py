import pytest
from factories import NOW, TIMESTAMPS
from sqlalchemy import delete, func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shodoukan_practice.infrastructure.db.orm import (
    EntryCollectionORM,
    KanjiCollectionORM,
    PracticeEntryORM,
    UserORM,
    entry_collection_items,
)


def add_entry(session: Session, user: UserORM) -> PracticeEntryORM:
    entry = PracticeEntryORM(
        user_id=user.id, source_entry_id=1, is_common=True, **TIMESTAMPS
    )
    session.add(entry)
    session.flush()
    return entry


def add_collection(session: Session, user: UserORM, name: str) -> EntryCollectionORM:
    collection = EntryCollectionORM(user_id=user.id, name=name, **TIMESTAMPS)
    session.add(collection)
    session.flush()
    return collection


def link_count(session: Session) -> int:
    query = select(func.count()).select_from(entry_collection_items)
    return session.scalar(query) or 0


def test_collection_name_is_unique_per_user(session: Session, user: UserORM) -> None:
    add_collection(session, user, "verbs")
    with pytest.raises(IntegrityError):
        add_collection(session, user, "verbs")


def test_same_name_for_entry_and_kanji_collections(
    session: Session, user: UserORM
) -> None:
    add_collection(session, user, "N5")
    session.add(KanjiCollectionORM(user_id=user.id, name="N5", **TIMESTAMPS))
    session.commit()


def test_item_can_only_be_linked_once(session: Session, user: UserORM) -> None:
    entry = add_entry(session, user)
    collection = add_collection(session, user, "verbs")
    link = {"collection_id": collection.id, "entry_id": entry.id, "added_at": NOW}
    session.execute(insert(entry_collection_items).values(link))
    with pytest.raises(IntegrityError):
        session.execute(insert(entry_collection_items).values(link))


def test_deleting_entry_removes_its_links(session: Session, user: UserORM) -> None:
    entry = add_entry(session, user)
    collection = add_collection(session, user, "verbs")
    session.execute(
        insert(entry_collection_items).values(
            collection_id=collection.id, entry_id=entry.id, added_at=NOW
        )
    )
    session.delete(entry)
    session.commit()

    assert link_count(session) == 0
    assert session.get(EntryCollectionORM, collection.id) is not None


def test_deleting_user_cascades_to_library_and_collections(
    session: Session, user: UserORM
) -> None:
    entry = add_entry(session, user)
    collection = add_collection(session, user, "verbs")
    session.execute(
        insert(entry_collection_items).values(
            collection_id=collection.id, entry_id=entry.id, added_at=NOW
        )
    )
    session.commit()

    session.execute(delete(UserORM).where(UserORM.id == user.id))
    session.commit()

    assert session.scalars(select(PracticeEntryORM)).all() == []
    assert session.scalars(select(EntryCollectionORM)).all() == []
    assert link_count(session) == 0
