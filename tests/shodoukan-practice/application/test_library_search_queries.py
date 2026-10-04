import pytest
from factories import (
    make_entry,
    make_entry_collection,
    make_kanji,
    make_kanji_collection,
    make_word,
)
from sqlalchemy.orm import Session

from shodoukan_practice.application.queries import (
    SearchEntries,
    SearchKanji,
    build_search,
    resolve_scope,
)
from shodoukan_practice.domain.entities import EntryCollection
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.domain.gateways import KanaForms
from shodoukan_practice.domain.searches import (
    InCollection,
    LibrarySearch,
    NotInCollection,
    WholeLibrary,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanKanaGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
)

kana = ShodoukanKanaGateway()


@pytest.fixture
def entries(session: Session) -> SqlAlchemyPracticeEntryRepository:
    return SqlAlchemyPracticeEntryRepository(session)


@pytest.fixture
def collections(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def search_entries(
    entries: SqlAlchemyPracticeEntryRepository,
    collections: SqlAlchemyEntryCollectionRepository,
) -> SearchEntries:
    return SearchEntries(entries, collections, kana)


# --- build_search / resolve_scope ---------------------------------------------


def test_build_search_normalizes_the_query_and_adds_its_kana() -> None:
    assert build_search("  Taberu ", "eng", None, kana) == LibrarySearch(
        text="taberu", kana=KanaForms("たべる", "タベル"), meaning_lang="eng"
    )
    assert build_search("water", None, True, kana) == LibrarySearch(
        text="water", active=True
    )


def test_build_search_with_blank_text_searches_nothing() -> None:
    assert build_search("   ", "", False, kana) == LibrarySearch(active=False)
    assert build_search(None, None, None, kana) == LibrarySearch()


def test_resolve_scope(user: UserORM) -> None:
    collection = make_entry_collection(user.id)

    def get(_: int) -> EntryCollection:
        return collection

    assert resolve_scope(get, None, None) == WholeLibrary()
    assert resolve_scope(get, 1, None) == InCollection(collection)
    assert resolve_scope(get, None, 1) == NotInCollection(collection)
    with pytest.raises(ValueError):
        resolve_scope(get, 1, 1)


# --- SearchEntries --------------------------------------------------------------


def test_library_pages_with_a_total_and_filters_by_active(
    search_entries: SearchEntries,
    entries: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    first = entries.add(make_entry(user.id, 1))
    second = entries.add(make_entry(user.id, 2, is_active=False))
    entries.add(make_entry(other_user.id, 1))

    page = search_entries.execute(user.id, limit=1, offset=0)

    assert page.items == [second]
    assert (page.total, page.limit, page.offset) == (2, 1, 0)
    active = search_entries.execute(user.id, active=True)
    assert (active.items, active.total) == ([first], 1)


def test_library_search_converts_romaji(
    search_entries: SearchEntries,
    entries: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
) -> None:
    eat = entries.add(make_word(user.id, 1, "食べる", "たべる", [("to eat", "eng")]))
    entries.add(make_word(user.id, 2, "水", "みず", [("water", "eng")]))

    assert search_entries.execute(user.id, text="Taberu").items == [eat]
    assert search_entries.execute(user.id, text="eat", meaning_lang="eng").items == [
        eat
    ]


def test_collection_pages_through_its_items_and_filters_by_active(
    search_entries: SearchEntries,
    entries: SqlAlchemyPracticeEntryRepository,
    collections: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
) -> None:
    verbs = collections.add(make_entry_collection(user.id))
    first = entries.add(make_entry(user.id, 1))
    inactive = entries.add(make_entry(user.id, 2, is_active=False))
    third = entries.add(make_entry(user.id, 3))
    entries.add(make_entry(user.id, 4))  # not in the collection
    for item in (first, inactive, third):
        collections.add_item(verbs, item)
    assert verbs.id is not None

    page = search_entries.execute(user.id, in_collection=verbs.id, limit=1)
    assert (page.items, page.total) == ([first], 3)
    rest = search_entries.execute(user.id, in_collection=verbs.id, offset=1)
    assert rest.items == [inactive, third]
    active = search_entries.execute(user.id, in_collection=verbs.id, active=True)
    assert (active.items, active.total) == ([first, third], 2)
    asked = search_entries.execute(user.id, in_collection=verbs.id, active=False)
    assert asked.items == [inactive]


def test_not_in_collection_lists_what_can_still_be_added(
    search_entries: SearchEntries,
    entries: SqlAlchemyPracticeEntryRepository,
    collections: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
) -> None:
    verbs = collections.add(make_entry_collection(user.id))
    added = entries.add(make_entry(user.id, 1))
    left = entries.add(make_entry(user.id, 2))
    collections.add_item(verbs, added)
    assert verbs.id is not None

    page = search_entries.execute(user.id, not_in_collection=verbs.id)

    assert (page.items, page.total) == ([left], 1)


def test_another_users_collection_is_not_found(
    search_entries: SearchEntries,
    collections: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    verbs = collections.add(make_entry_collection(user.id))
    assert verbs.id is not None

    with pytest.raises(EntityNotFoundError):
        search_entries.execute(other_user.id, in_collection=verbs.id)
    with pytest.raises(EntityNotFoundError):
        search_entries.execute(other_user.id, not_in_collection=verbs.id)


# --- SearchKanji ------------------------------------------------------------------


def test_search_kanji_in_the_library_and_a_collection(
    session: Session, user: UserORM
) -> None:
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    kanji_collections = SqlAlchemyKanjiCollectionRepository(session)
    query = SearchKanji(kanji, kanji_collections, kana)
    n5 = kanji_collections.add(make_kanji_collection(user.id))
    item = kanji.add(make_kanji(user.id))
    kanji_collections.add_item(n5, item)
    assert n5.id is not None

    assert query.execute(user.id).items == [item]
    assert query.execute(user.id, text="taberu").items == [item]  # た.べる
    assert query.execute(user.id, in_collection=n5.id).items == [item]
    assert query.execute(user.id, not_in_collection=n5.id).items == []
    with pytest.raises(EntityNotFoundError):
        query.execute(user.id, in_collection=n5.id + 1)
