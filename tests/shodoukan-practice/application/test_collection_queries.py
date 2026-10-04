import pytest
from factories import (
    make_entry_collection,
    make_kanji,
    make_kanji_collection,
)
from sqlalchemy.orm import Session

from shodoukan_practice.application.queries import (
    GetEntryCollection,
    GetKanjiCollection,
    ListEntryCollections,
    ListKanjiCollections,
)
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def collections(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def kanji_collections(session: Session) -> SqlAlchemyKanjiCollectionRepository:
    return SqlAlchemyKanjiCollectionRepository(session)


def test_list_returns_only_the_users_collections_by_name(
    collections: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    verbs = collections.add(make_entry_collection(user.id, "verbs"))
    adjectives = collections.add(make_entry_collection(user.id, "adjectives"))
    collections.add(make_entry_collection(other_user.id, "theirs"))

    assert ListEntryCollections(collections).execute(user.id) == [adjectives, verbs]


def test_get_another_users_collection_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    verbs = collections.add(make_entry_collection(user.id))
    assert verbs.id is not None

    assert GetEntryCollection(collections).execute(user.id, verbs.id) == verbs
    with pytest.raises(EntityNotFoundError):
        GetEntryCollection(collections).execute(other_user.id, verbs.id)


def test_kanji_queries(
    kanji_collections: SqlAlchemyKanjiCollectionRepository,
    session: Session,
    user: UserORM,
) -> None:
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    n5 = kanji_collections.add(make_kanji_collection(user.id))
    item = kanji.add(make_kanji(user.id))
    kanji_collections.add_item(n5, item)
    assert n5.id is not None

    assert ListKanjiCollections(kanji_collections).execute(user.id) == [n5]
    assert GetKanjiCollection(kanji_collections).execute(user.id, n5.id) == n5
    with pytest.raises(EntityNotFoundError):
        GetKanjiCollection(kanji_collections).execute(user.id, n5.id + 1)
