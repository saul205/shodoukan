import pytest
from factories import make_entry_collection, make_kanji_collection
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import (
    CreateOwnEntry,
    ImportEntry,
    ImportKanji,
)
from shodoukan_practice.domain.exceptions import (
    DictionaryItemNotFoundError,
    EntityNotFoundError,
)
from shodoukan_practice.infrastructure.db.orm import PracticeEntryORM, UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)


@pytest.fixture
def import_entry(session: Session, dictionary: Dictionary) -> ImportEntry:
    return ImportEntry(
        ShodoukanDictionaryGateway(dictionary),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
    )


@pytest.fixture
def import_kanji(session: Session, dictionary: Dictionary) -> ImportKanji:
    return ImportKanji(
        ShodoukanDictionaryGateway(dictionary),
        SqlAlchemyPracticeKanjiRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


def test_import_entry_adds_it_to_the_library(
    import_entry: ImportEntry, user: UserORM, session: Session
) -> None:
    result = import_entry.execute(user.id, 1000001)

    assert result.created is True
    assert result.item.id is not None
    assert result.item.source_entry_id == 1000001
    stored = SqlAlchemyPracticeEntryRepository(session).get(result.item.id, user.id)
    assert stored == result.item


def test_import_entry_twice_returns_the_existing_copy(
    import_entry: ImportEntry, user: UserORM
) -> None:
    first = import_entry.execute(user.id, 1000001)
    again = import_entry.execute(user.id, 1000001)

    assert again.created is False
    assert again.item == first.item


def test_each_user_gets_their_own_copy(
    import_entry: ImportEntry, user: UserORM, other_user: UserORM
) -> None:
    mine = import_entry.execute(user.id, 1000001)
    theirs = import_entry.execute(other_user.id, 1000001)

    assert theirs.created is True
    assert theirs.item.id != mine.item.id
    assert theirs.item.user_id == other_user.id


def test_import_unknown_entry_fails(import_entry: ImportEntry, user: UserORM) -> None:
    with pytest.raises(DictionaryItemNotFoundError):
        import_entry.execute(user.id, 999)


def test_import_kanji_adds_it_then_returns_the_existing_copy(
    import_kanji: ImportKanji, user: UserORM
) -> None:
    first = import_kanji.execute(user.id, "食")
    again = import_kanji.execute(user.id, "食")

    assert first.created is True
    assert first.item.literal == "食"
    assert [m.text for m in first.item.meanings] == ["eat", "food"]
    assert again.created is False
    assert again.item == first.item


def test_import_unknown_kanji_fails(import_kanji: ImportKanji, user: UserORM) -> None:
    with pytest.raises(DictionaryItemNotFoundError):
        import_kanji.execute(user.id, "龘")


# --- Importing into collections ---


def test_import_entry_puts_it_in_the_collections(
    import_entry: ImportEntry, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    verbs = collections.add(make_entry_collection(user.id, "verbs"))
    n5 = collections.add(make_entry_collection(user.id, "N5"))
    assert verbs.id is not None and n5.id is not None

    result = import_entry.execute(user.id, 1000001, [verbs.id, n5.id, verbs.id])

    assert result.created is True
    tags = collections.list_for_item(result.item)
    assert sorted(c.name for c in tags) == ["N5", "verbs"]


def test_import_entry_already_imported_still_joins_the_collection(
    import_entry: ImportEntry, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    verbs = collections.add(make_entry_collection(user.id))
    assert verbs.id is not None
    first = import_entry.execute(user.id, 1000001)

    again = import_entry.execute(user.id, 1000001, [verbs.id])
    import_entry.execute(user.id, 1000001, [verbs.id])

    assert again.created is False
    assert again.item == first.item
    assert collections.item_ids([verbs]) == {first.item.id}


@pytest.mark.parametrize("owner", ["other_user", "nobody"])
def test_import_entry_into_a_foreign_collection_imports_nothing(
    import_entry: ImportEntry,
    user: UserORM,
    other_user: UserORM,
    session: Session,
    owner: str,
) -> None:
    collection_id = 999
    if owner == "other_user":
        theirs = SqlAlchemyEntryCollectionRepository(session).add(
            make_entry_collection(other_user.id)
        )
        assert theirs.id is not None
        collection_id = theirs.id

    with pytest.raises(EntityNotFoundError):
        import_entry.execute(user.id, 1000001, [collection_id])

    entries = SqlAlchemyPracticeEntryRepository(session)
    assert entries.get_by_source_entry_id(1000001, user.id) is None


def test_import_kanji_puts_it_in_the_collection(
    import_kanji: ImportKanji, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    n5 = collections.add(make_kanji_collection(user.id))
    assert n5.id is not None

    result = import_kanji.execute(user.id, "食", [n5.id])

    assert [c.name for c in collections.list_for_item(result.item)] == ["N5"]


def test_import_kanji_into_an_unknown_collection_imports_nothing(
    import_kanji: ImportKanji, user: UserORM, session: Session
) -> None:
    with pytest.raises(EntityNotFoundError):
        import_kanji.execute(user.id, "食", [999])

    assert (
        SqlAlchemyPracticeKanjiRepository(session).get_by_literal("食", user.id) is None
    )


# --- Words of the user's own ---


@pytest.fixture
def create_own(session: Session) -> CreateOwnEntry:
    return CreateOwnEntry(
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
    )


def test_create_own_entry_stores_it_in_the_collections(
    create_own: CreateOwnEntry, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    counters = collections.add(make_entry_collection(user.id, "counters"))
    assert counters.id is not None

    entry = create_own.execute(
        user.id, ["三匹"], ["さんびき"], "three animals", "eng", [counters.id]
    )

    assert entry.id is not None and entry.is_own
    stored = SqlAlchemyPracticeEntryRepository(session).get(entry.id, user.id)
    assert stored == entry
    assert [c.name for c in collections.list_for_item(entry)] == ["counters"]


def test_create_own_entry_in_an_unknown_collection_creates_nothing(
    create_own: CreateOwnEntry, user: UserORM, other_user: UserORM, session: Session
) -> None:
    theirs = SqlAlchemyEntryCollectionRepository(session).add(
        make_entry_collection(other_user.id, "theirs")
    )
    assert theirs.id is not None

    with pytest.raises(EntityNotFoundError):
        create_own.execute(user.id, [], ["ねこ"], "cat", "eng", [theirs.id])

    assert session.query(PracticeEntryORM).count() == 0
