from datetime import timedelta
from typing import Any

import pytest
from factories import NOW, make_entry, make_entry_collection, make_word
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import EntryCollection, PracticeGloss
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.domain.gateways import KanaForms
from shodoukan_practice.domain.searches import (
    InCollection,
    LibrarySearch,
    NotInCollection,
    SearchScope,
    WholeLibrary,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
)

# Searches without text: they list the scope, like the library pages.
EVERYTHING = LibrarySearch()
ACTIVE = LibrarySearch(active=True)
INACTIVE = LibrarySearch(active=False)
LIBRARY = WholeLibrary()


@pytest.fixture
def repo(session: Session) -> SqlAlchemyPracticeEntryRepository:
    return SqlAlchemyPracticeEntryRepository(session)


def test_add_assigns_ids_and_get_returns_it(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    added = repo.add(make_entry(user.id))
    session.expunge_all()

    assert added.id is not None
    assert all(g.id is not None for g in added.senses[0].glosses)
    assert repo.get(added.id, user.id) == added


def test_get_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_entry(user.id))
    assert added.id is not None
    assert repo.get(added.id, other_user.id) is None


def test_get_many_skips_other_users(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    mine = repo.add(make_entry(user.id, 1))
    theirs = repo.add(make_entry(other_user.id, 2))
    ids = [e.id for e in (mine, theirs) if e.id is not None]

    assert repo.get_many(ids, user.id) == [mine]


def test_update_edits_adds_and_removes_nested_items(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    entry = repo.add(make_entry(user.id))
    glosses = entry.senses[0].glosses
    glosses[0].enabled = False
    del glosses[1]
    glosses.append(
        PracticeGloss(id=None, text="to dine", lang="eng", type=None, origin="added")
    )

    updated = repo.update(entry)
    session.expunge_all()
    assert entry.id is not None
    stored = repo.get(entry.id, user.id)

    assert stored == updated
    assert stored is not None
    texts = [(g.text, g.enabled, g.origin) for g in stored.senses[0].glosses]
    assert texts == [("to eat", False, "imported"), ("to dine", True, "added")]


def test_update_cannot_move_an_entry_to_another_user(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    entry = repo.add(make_entry(user.id))
    stolen = entry.model_copy(update={"user_id": other_user.id})

    with pytest.raises(EntityNotFoundError):
        repo.update(stolen)


def test_update_of_unsaved_entry_fails(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    with pytest.raises(EntityNotFoundError):
        repo.update(make_entry(user.id))


def test_get_by_source_entry_id_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_entry(user.id))

    assert repo.get_by_source_entry_id(1000001, user.id) == added
    assert repo.get_by_source_entry_id(1000001, other_user.id) is None


def test_add_if_absent_creates_once(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    first, created = repo.add_if_absent(make_entry(user.id))
    again, created_again = repo.add_if_absent(make_entry(user.id))

    assert created is True
    assert created_again is False
    assert again == first
    # The failed insert only rolled back its savepoint: the session still works.
    session.commit()
    assert first.id is not None
    assert repo.get(first.id, user.id) == first


def test_practice_ids_by_source_entry_id_lists_only_the_users_imports(
    repo: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    mine = repo.add(make_entry(user.id, 1000001))
    repo.add(make_entry(other_user.id, 1000002))

    found = repo.practice_ids_by_source_entry_id([1000001, 1000002, 999], user.id)

    assert found == {1000001: mine.id}


def test_find_without_text_is_newest_first_and_paginated(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    old = repo.add(make_entry(user.id, 1))
    new = repo.add(
        make_entry(user.id, 2).model_copy(update={"created_at": NOW + timedelta(1)})
    )
    same_time_later_id = repo.add(make_entry(user.id, 3))
    repo.add(make_entry(other_user.id, 1))

    assert repo.find(user.id, EVERYTHING, LIBRARY, limit=10, offset=0) == [
        new,
        same_time_later_id,
        old,
    ]
    assert repo.find(user.id, EVERYTHING, LIBRARY, limit=1, offset=1) == [
        same_time_later_id
    ]
    assert repo.count(user.id, EVERYTHING, LIBRARY) == 3


def test_find_without_text_filters_by_active(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    active = repo.add(make_entry(user.id, 1))
    inactive = repo.add(make_entry(user.id, 2, is_active=False))

    assert repo.find(user.id, ACTIVE, LIBRARY, 10, 0) == [active]
    assert repo.find(user.id, INACTIVE, LIBRARY, 10, 0) == [inactive]
    assert repo.count(user.id, INACTIVE, LIBRARY) == 1


def test_count_without_items_is_zero(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    assert repo.count(user.id, EVERYTHING, LIBRARY) == 0


def test_delete_removes_the_item_and_its_links(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    collection = collections.add(make_entry_collection(user.id))
    item = repo.add(make_entry(user.id))
    collections.add_item(collection, item)
    assert item.id is not None

    repo.delete(item)

    assert repo.get(item.id, user.id) is None
    assert collections.item_ids([collection]) == set()
    assert collections.get(collection.id or 0, user.id) == collection


def test_delete_of_another_users_item_fails(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    item = repo.add(make_entry(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.delete(item.model_copy(update={"user_id": other_user.id}))
    assert item.id is not None
    assert repo.get(item.id, user.id) is not None


def test_count_in_a_collection_filters_by_active(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    collection = collections.add(make_entry_collection(user.id))
    collections.add_item(collection, repo.add(make_entry(user.id, 1)))
    collections.add_item(collection, repo.add(make_entry(user.id, 2, is_active=False)))

    assert repo.count(user.id, EVERYTHING, InCollection(collection)) == 2
    assert repo.count(user.id, ACTIVE, InCollection(collection)) == 1
    inactive = LibrarySearch(active=False)
    assert repo.count(user.id, inactive, InCollection(collection)) == 1


def test_update_persists_added_edited_and_removed_meanings(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    entry = repo.add(make_entry(user.id))
    sense_id = entry.senses[0].id
    assert sense_id is not None

    entry.add_gloss(sense_id, "to scoff", "eng")
    entry = repo.update(entry)
    added = entry.senses[0].glosses[-1]
    assert added.id is not None and added.origin == "added"

    entry.edit_gloss(added.id, "to wolf down")
    entry.set_sense_notes(sense_id, "casual")
    entry = repo.update(entry)
    session.expunge_all()
    stored = repo.get(entry.id or 0, user.id)
    assert stored is not None
    assert stored.senses[0].glosses[-1].text == "to wolf down"
    assert stored.senses[0].notes == "casual"

    stored.remove_gloss(added.id)
    repo.update(stored)
    session.expunge_all()
    reloaded = repo.get(entry.id or 0, user.id)
    assert reloaded is not None
    assert [g.origin for g in reloaded.senses[0].glosses] == ["imported", "imported"]


# --- Search (find / count) ----------------------------------------------------


def _search(text: str, *kana: str, **filters: Any) -> LibrarySearch:
    """A search for `text`; `kana` are its hiragana and katakana forms."""
    forms = KanaForms(*kana) if kana else None
    return LibrarySearch(text=text, kana=forms, **filters)


def _found(
    repo: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
    search: LibrarySearch,
    scope: SearchScope[EntryCollection] | None = None,
) -> list[str]:
    """Readings of the entries found, in order; checks `count` agrees."""
    scope = scope or WholeLibrary()
    found = repo.find(user.id, search, scope, limit=50, offset=0)
    assert repo.count(user.id, search, scope) == len(found)
    return [entry.readings[0].text for entry in found]


def test_find_ranks_exact_then_word_start_then_anywhere(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    # Created so that the newest is the weakest match.
    repo.add(make_word(user.id, 1, "食", "しょく", [("eat", "eng")]))
    repo.add(
        make_word(
            user.id,
            2,
            "食べる",
            "たべる",
            [("to eat", "eng")],
            created_at=NOW + timedelta(days=1),
        )
    )
    repo.add(
        make_word(
            user.id,
            3,
            None,
            "ぐれいと",
            [("great", "eng")],
            created_at=NOW + timedelta(days=2),
        )
    )
    repo.add(make_word(user.id, 4, "水", "みず", [("water", "eng")]))

    assert _found(repo, user, _search("eat")) == ["しょく", "たべる", "ぐれいと"]


def test_find_by_romaji_and_katakana_reading(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    repo.add(make_word(user.id, 1, "食べる", "たべる", [("to eat", "eng")]))
    repo.add(make_word(user.id, 2, None, "パン", [("bread", "eng")]))

    assert _found(repo, user, _search("taberu", "たべる", "タベル")) == ["たべる"]
    assert _found(repo, user, _search("pan", "ぱん", "パン")) == ["パン"]
    assert _found(repo, user, _search("食")) == ["たべる"]


def test_find_looks_in_hidden_and_own_meanings(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    entry = repo.add(make_word(user.id, 1, "食べる", "たべる", [("to eat", "eng")]))
    sense = entry.senses[0]
    assert sense.id is not None and sense.glosses[0].id is not None
    entry.set_enabled("glosses", sense.glosses[0].id, False)
    entry.add_gloss(sense.id, "to devour", "eng")
    repo.update(entry)

    assert _found(repo, user, _search("eat")) == ["たべる"]
    assert _found(repo, user, _search("devour")) == ["たべる"]


def test_find_only_in_meanings_of_the_language(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    repo.add(
        make_word(user.id, 1, "食べる", "たべる", [("to eat", "eng"), ("comer", "spa")])
    )

    assert _found(repo, user, _search("comer", meaning_lang="eng")) == []
    assert _found(repo, user, _search("comer", meaning_lang="spa")) == ["たべる"]
    assert _found(repo, user, _search("comer")) == ["たべる"]


def test_find_romaji_matches_both_reading_and_meaning(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    # "same" is the English word and さめ (shark): both are exact matches,
    # so the newer one comes first.
    repo.add(make_word(user.id, 1, "同じ", "おなじ", [("same", "eng")]))
    repo.add(
        make_word(
            user.id,
            2,
            "鮫",
            "さめ",
            [("shark", "eng")],
            created_at=NOW + timedelta(days=1),
        )
    )

    assert _found(repo, user, _search("same", "さめ", "サメ")) == ["さめ", "おなじ"]


def test_find_treats_wildcards_literally(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    repo.add(make_word(user.id, 1, None, "ひゃく", [("100% sure", "eng")]))
    repo.add(make_word(user.id, 2, None, "みず", [("water", "eng")]))

    assert _found(repo, user, _search("%")) == ["ひゃく"]
    assert _found(repo, user, _search("_")) == []


def test_find_pages_through_the_matches(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM
) -> None:
    for i in range(5):
        repo.add(
            make_word(
                user.id,
                i,
                None,
                f"み{i}",
                [("water", "eng")],
                created_at=NOW + timedelta(days=i),
            )
        )
    search = _search("water")

    pages = [
        repo.find(user.id, search, WholeLibrary(), limit=2, offset=offset)
        for offset in (0, 2, 4)
    ]

    assert [[e.readings[0].text for e in page] for page in pages] == [
        ["み4", "み3"],
        ["み2", "み1"],
        ["み0"],
    ]
    assert repo.count(user.id, search, WholeLibrary()) == 5


def test_find_in_and_out_of_a_collection(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    collection = collections.add(make_entry_collection(user.id))
    eat = repo.add(make_word(user.id, 1, "食べる", "たべる", [("to eat", "eng")]))
    drink = repo.add(
        make_word(
            user.id,
            2,
            "飲む",
            "のむ",
            [("to drink", "eng")],
            created_at=NOW + timedelta(days=1),
        )
    )
    repo.add(make_word(user.id, 3, "食う", "くう", [("to eat", "eng")]))
    collections.add_item(collection, drink)
    collections.add_item(collection, eat)

    # In the collection: its items only, in the order they were added.
    assert _found(repo, user, LibrarySearch(), InCollection(collection)) == [
        "のむ",
        "たべる",
    ]
    assert _found(repo, user, _search("eat"), InCollection(collection)) == ["たべる"]
    # Out of it: what can still be added.
    assert _found(repo, user, _search("eat"), NotInCollection(collection)) == ["くう"]


def test_find_is_scoped_to_the_user(
    repo: SqlAlchemyPracticeEntryRepository, user: UserORM, other_user: UserORM
) -> None:
    repo.add(make_word(other_user.id, 1, "食べる", "たべる", [("to eat", "eng")]))

    assert _found(repo, user, _search("eat")) == []
    assert _found(repo, user, LibrarySearch()) == []
