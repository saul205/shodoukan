from uuid import UUID, uuid4

import pytest
from factories import TIMESTAMPS, make_entry, make_entry_collection
from sqlalchemy import select
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import (
    EntryCollection,
    PracticeEntry,
    SharedEntry,
    SharedEntryCollection,
)
from shodoukan_practice.domain.exceptions import (
    CollectionNameTakenError,
    CollectionOwnershipError,
    EntityNotFoundError,
)
from shodoukan_practice.domain.searches import (
    InCollection,
    LibrarySearch,
    PublicCollectionSearch,
)
from shodoukan_practice.infrastructure.db.orm import UserORM, entry_collection_items
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
)

# Searches without text: they list the scope, like the library pages.
ACTIVE = LibrarySearch(active=True)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def items(session: Session, user: UserORM) -> list[PracticeEntry]:
    item_repo = SqlAlchemyPracticeEntryRepository(session)
    return [
        item_repo.add(make_entry(user.id, 1)),
        item_repo.add(make_entry(user.id, 2)),
        item_repo.add(make_entry(user.id, 3, is_active=False)),
    ]


def test_add_get_and_list_for_user(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    b = repo.add(make_entry_collection(user.id, "b"))
    a = repo.add(make_entry_collection(user.id, "a"))
    repo.add(make_entry_collection(other_user.id, "theirs"))

    assert b.id is not None
    assert repo.get(b.id, user.id) == b
    assert repo.get(b.id, other_user.id) is None
    assert repo.list_for_user(user.id) == [a, b]


def test_update_renames(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    renamed = repo.update(collection.model_copy(update={"name": "renamed"}))

    assert collection.id is not None
    assert repo.get(collection.id, user.id) == renamed
    assert renamed.name == "renamed"


def test_update_of_another_users_collection_fails(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.update(collection.model_copy(update={"user_id": other_user.id}))


def test_add_item_is_idempotent(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    repo.add_item(collection, items[0])
    repo.add_item(collection, items[0])

    assert repo.item_ids([collection]) == {items[0].id}


def test_add_item_of_another_user_fails(
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    other_user: UserORM,
    items: list[PracticeEntry],
) -> None:
    theirs = repo.add(make_entry_collection(other_user.id))
    with pytest.raises(CollectionOwnershipError):
        repo.add_item(theirs, items[0])


def test_remove_item(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    repo.add_item(collection, items[0])
    repo.remove_item(collection, items[0])
    repo.remove_item(collection, items[0])

    assert repo.item_ids([collection]) == set()


def test_find_in_a_collection_paginates_and_filters_by_active(
    session: Session,
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    items: list[PracticeEntry],
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    for item in items:
        repo.add_item(collection, item)
    item_repo = SqlAlchemyPracticeEntryRepository(session)

    in_collection = InCollection(collection)
    first = item_repo.find(user.id, ACTIVE, in_collection, limit=1, offset=0)
    rest = item_repo.find(user.id, ACTIVE, in_collection, limit=10, offset=1)
    every = item_repo.find(user.id, LibrarySearch(), in_collection, limit=10, offset=0)

    assert first == [items[0]]
    assert rest == [items[1]]
    assert every == items


def test_list_for_item_returns_its_collections(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    b = repo.add(make_entry_collection(user.id, "b"))
    a = repo.add(make_entry_collection(user.id, "a"))
    repo.add(make_entry_collection(user.id, "unrelated"))
    repo.add_item(b, items[0])
    repo.add_item(a, items[0])

    assert repo.list_for_item(items[0]) == [a, b]


def test_item_ids_are_distinct_and_active_only(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, items: list[PracticeEntry]
) -> None:
    one = repo.add(make_entry_collection(user.id, "one"))
    two = repo.add(make_entry_collection(user.id, "two"))
    repo.add_item(one, items[0])
    repo.add_item(two, items[0])
    repo.add_item(two, items[1])
    repo.add_item(two, items[2])  # inactive

    assert repo.item_ids([one, two]) == {items[0].id, items[1].id}


def test_delete_keeps_the_items(
    session: Session,
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    items: list[PracticeEntry],
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    repo.add_item(collection, items[0])
    repo.delete(collection)

    assert collection.id is not None
    assert items[0].id is not None
    assert repo.get(collection.id, user.id) is None
    assert repo.list_for_item(items[0]) == []
    assert (
        SqlAlchemyPracticeEntryRepository(session).get(items[0].id, user.id) is not None
    )


def test_add_with_a_taken_name_fails_and_keeps_the_session_usable(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    kept = repo.add(make_entry_collection(user.id, "same"))
    theirs = repo.add(make_entry_collection(other_user.id, "same"))

    with pytest.raises(CollectionNameTakenError):
        repo.add(make_entry_collection(user.id, "same"))

    assert theirs.name == "same"  # names are unique per user only
    assert repo.list_for_user(user.id) == [kept]


def test_update_to_a_taken_name_fails(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    repo.add(make_entry_collection(user.id, "a"))
    b = repo.add(make_entry_collection(user.id, "b"))

    with pytest.raises(CollectionNameTakenError):
        repo.update(b.model_copy(update={"name": "a"}))

    assert b.id is not None
    assert repo.get(b.id, user.id) == b


def test_add_keeps_where_it_was_copied_from(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, session: Session
) -> None:
    collection = make_entry_collection(user.id, "N5").model_copy(
        update={"source_collection_id": 42}
    )
    added = repo.add(collection)
    session.expunge_all()
    assert added.id is not None
    stored = repo.get(added.id, user.id)
    assert stored is not None
    assert stored.source_collection_id == 42


# --- Sharing ---


def published(
    repo: SqlAlchemyEntryCollectionRepository,
    user_id: UUID,
    name: str,
    description: str | None = None,
) -> EntryCollection:
    collection = repo.add(
        make_entry_collection(user_id, name).model_copy(
            update={"description": description}
        )
    )
    collection.publish()
    collection = repo.update(collection)
    shared = SharedEntryCollection(
        id=collection.id,
        name=name,
        items=[SharedEntry(source_entry_id=1), SharedEntry(source_entry_id=2)],
    )
    repo.save_publication(collection, shared, includes_notes=False)
    return collection


@pytest.fixture
def third_user(session: Session) -> UserORM:
    row = UserORM(id=uuid4(), username="Tanaka", **TIMESTAMPS)
    session.add(row)
    session.flush()
    return row


def test_publication_is_stored_and_replaced(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, session: Session
) -> None:
    collection = published(repo, user.id, "N5")
    session.expunge_all()

    stored = repo.get_publication(collection)
    assert stored is not None
    assert [i.source_entry_id for i in stored.items] == [1, 2]
    repo.save_publication(collection, SharedEntryCollection(name="N5"), True)
    again = repo.get_publication(collection)
    assert again is not None and again.items == []
    private = repo.add(make_entry_collection(user.id, "private"))
    assert repo.get_publication(private) is None


def test_get_public_is_any_owners_but_only_public(
    repo: SqlAlchemyEntryCollectionRepository, user: UserORM, other_user: UserORM
) -> None:
    mine = published(repo, user.id, "N5")
    private = repo.add(make_entry_collection(user.id, "private"))
    assert mine.id is not None and private.id is not None

    found = repo.get_public(mine.id)
    assert found is not None and found.user_id == user.id
    assert repo.get_public(private.id) is None
    mine.unpublish()
    repo.update(mine)
    assert repo.get_public(mine.id) is None


def test_find_public_filters_by_owner_and_text(
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    other_user: UserORM,
    third_user: UserORM,
) -> None:
    published(repo, user.id, "Verbos N5", "godan")
    published(repo, other_user.id, "Kitchen")
    published(repo, third_user.id, "Animals", "Counters and GODAN pairs")
    repo.add(make_entry_collection(other_user.id, "hidden"))

    def names(search: PublicCollectionSearch) -> list[str]:
        found = repo.find_public(search, user.id, 10, 0)
        assert repo.count_public(search, user.id) == len(found)
        return sorted(s.collection.name for s in found)

    assert names(PublicCollectionSearch()) == ["Animals", "Kitchen", "Verbos N5"]
    assert names(PublicCollectionSearch(owner="mine")) == ["Verbos N5"]
    assert names(PublicCollectionSearch(owner="others")) == ["Animals", "Kitchen"]
    assert names(PublicCollectionSearch(text="godan")) == ["Animals", "Verbos N5"]
    assert names(PublicCollectionSearch(text="tanaka")) == ["Animals"]
    assert names(PublicCollectionSearch(text="100%")) == []


def test_downloads_count_users_once_and_never_the_owner(
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    other_user: UserORM,
    third_user: UserORM,
) -> None:
    popular = published(repo, user.id, "Popular")
    recent = published(repo, user.id, "Recent")
    repo.record_download(popular, other_user.id, 1)
    repo.record_download(popular, other_user.id, 2)  # again: the latest version
    repo.record_download(popular, third_user.id, 1)
    repo.record_download(popular, user.id, 1)  # the owner

    by_popularity = repo.find_public(PublicCollectionSearch(), other_user.id, 10, 0)
    assert [(s.collection.name, s.downloads) for s in by_popularity] == [
        ("Popular", 2),
        ("Recent", 0),
    ]
    assert by_popularity[0].viewer_version == 2
    assert by_popularity[0].owner_username == "saul"
    assert by_popularity[0].item_count == 2
    by_date = repo.find_public(
        PublicCollectionSearch(sort="recent"), other_user.id, 10, 0
    )
    assert [s.collection.name for s in by_date] == ["Recent", "Popular"]
    summary = repo.public_summary(recent, third_user.id)
    assert (summary.downloads, summary.viewer_version) == (0, None)


def test_add_item_marks_what_the_source_put(
    repo: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    items: list[PracticeEntry],
    session: Session,
) -> None:
    collection = repo.add(make_entry_collection(user.id))
    repo.add_item(collection, items[0], from_source=True)
    repo.add_item(collection, items[1])
    repo.add_item(collection, items[1], from_source=True)  # linked already: kept

    rows = session.execute(
        select(
            entry_collection_items.c.entry_id, entry_collection_items.c.from_source
        ).where(entry_collection_items.c.collection_id == collection.id)
    ).all()
    assert sorted(rows) == [(items[0].id, True), (items[1].id, False)]
