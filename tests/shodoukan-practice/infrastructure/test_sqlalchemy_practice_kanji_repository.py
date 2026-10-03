from datetime import timedelta
from typing import Any

import pytest
from factories import NOW, make_kanji, make_kanji_collection, make_kanji_with
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import KanjiCollection, PracticeReadingItem
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
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeKanjiRepository,
)

# Searches without text: they list the scope, like the library pages.
EVERYTHING = LibrarySearch()
ACTIVE = LibrarySearch(active=True)
INACTIVE = LibrarySearch(active=False)
LIBRARY = WholeLibrary()


@pytest.fixture
def repo(session: Session) -> SqlAlchemyPracticeKanjiRepository:
    return SqlAlchemyPracticeKanjiRepository(session)


def test_add_then_get(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    added = repo.add(make_kanji(user.id))
    session.expunge_all()

    assert added.id is not None
    assert repo.get(added.id, user.id) == added


def test_get_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_kanji(user.id))
    assert added.id is not None
    assert repo.get(added.id, other_user.id) is None


def test_get_many_skips_other_users(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    mine = repo.add(make_kanji(user.id, "食"))
    theirs = repo.add(make_kanji(other_user.id, "水"))
    ids = [k.id for k in (mine, theirs) if k.id is not None]

    assert repo.get_many(ids, user.id) == [mine]


def test_update_toggles_and_adds_readings(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    kanji = repo.add(make_kanji(user.id))
    kanji.kun_readings[1].enabled = False
    kanji.nanori.append(PracticeReadingItem(id=None, text="あき"))

    repo.update(kanji)
    session.expunge_all()
    assert kanji.id is not None
    stored = repo.get(kanji.id, user.id)

    assert stored is not None
    assert [(r.text, r.enabled) for r in stored.kun_readings] == [
        ("た.べる", True),
        ("く.う", False),
    ]
    assert [r.text for r in stored.nanori] == ["あき"]


def test_update_cannot_move_kanji_to_another_user(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    kanji = repo.add(make_kanji(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.update(kanji.model_copy(update={"user_id": other_user.id}))


def test_get_by_literal_is_scoped_to_the_owner(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    added = repo.add(make_kanji(user.id))

    assert repo.get_by_literal("食", user.id) == added
    assert repo.get_by_literal("食", other_user.id) is None


def test_add_if_absent_creates_once(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    first, created = repo.add_if_absent(make_kanji(user.id))
    again, created_again = repo.add_if_absent(make_kanji(user.id))

    assert created is True
    assert created_again is False
    assert again == first
    # The failed insert only rolled back its savepoint: the session still works.
    session.commit()
    assert first.id is not None
    assert repo.get(first.id, user.id) == first


def test_practice_ids_by_literal_lists_only_the_users_imports(
    repo: SqlAlchemyPracticeKanjiRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    mine = repo.add(make_kanji(user.id, "食"))
    repo.add(make_kanji(other_user.id, "水"))

    found = repo.practice_ids_by_literal(["食", "水", "龘"], user.id)

    assert found == {"食": mine.id}


def test_find_without_text_is_newest_first_and_paginated(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    old = repo.add(make_kanji(user.id, "一"))
    new = repo.add(
        make_kanji(user.id, "二").model_copy(update={"created_at": NOW + timedelta(1)})
    )
    same_time_later_id = repo.add(make_kanji(user.id, "三"))
    repo.add(make_kanji(other_user.id, "一"))

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
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM
) -> None:
    active = repo.add(make_kanji(user.id, "一"))
    inactive = repo.add(make_kanji(user.id, "二", is_active=False))

    assert repo.find(user.id, ACTIVE, LIBRARY, 10, 0) == [active]
    assert repo.find(user.id, INACTIVE, LIBRARY, 10, 0) == [inactive]
    assert repo.count(user.id, INACTIVE, LIBRARY) == 1


def test_count_without_items_is_zero(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM
) -> None:
    assert repo.count(user.id, EVERYTHING, LIBRARY) == 0


def test_delete_removes_the_item_and_its_links(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    collection = collections.add(make_kanji_collection(user.id))
    item = repo.add(make_kanji(user.id))
    collections.add_item(collection, item)
    assert item.id is not None

    repo.delete(item)

    assert repo.get(item.id, user.id) is None
    assert collections.item_ids([collection]) == set()
    assert collections.get(collection.id or 0, user.id) == collection


def test_delete_of_another_users_item_fails(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, other_user: UserORM
) -> None:
    item = repo.add(make_kanji(user.id))
    with pytest.raises(EntityNotFoundError):
        repo.delete(item.model_copy(update={"user_id": other_user.id}))
    assert item.id is not None
    assert repo.get(item.id, user.id) is not None


def test_count_in_a_collection_can_keep_only_active_items(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    collection = collections.add(make_kanji_collection(user.id))
    collections.add_item(collection, repo.add(make_kanji(user.id, "一")))
    collections.add_item(
        collection, repo.add(make_kanji(user.id, "二", is_active=False))
    )

    assert repo.count(user.id, ACTIVE, InCollection(collection)) == 1
    assert repo.count(user.id, EVERYTHING, InCollection(collection)) == 2


# --- Search (find / count) ----------------------------------------------------


def _search(text: str, *kana: str, **filters: Any) -> LibrarySearch:
    """A search for `text`; `kana` are its hiragana and katakana forms."""
    forms = KanaForms(*kana) if kana else None
    return LibrarySearch(text=text, kana=forms, **filters)


def _found(
    repo: SqlAlchemyPracticeKanjiRepository,
    user: UserORM,
    search: LibrarySearch,
    scope: SearchScope[KanjiCollection] | None = None,
) -> list[str]:
    """Literals of the kanji found, in order; checks `count` agrees."""
    scope = scope or WholeLibrary()
    found = repo.find(user.id, search, scope, limit=50, offset=0)
    assert repo.count(user.id, search, scope) == len(found)
    return [kanji.literal for kanji in found]


def test_find_by_literal_and_by_a_word_containing_it(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM
) -> None:
    repo.add(make_kanji_with(user.id, "兄", meanings=[("elder brother", "en")]))
    repo.add(make_kanji_with(user.id, "弟", created_at=NOW + timedelta(days=1)))
    repo.add(make_kanji_with(user.id, "水"))

    assert _found(repo, user, _search("兄")) == ["兄"]
    # 兄弟 (kyoudai) contains both.
    assert _found(repo, user, _search("兄弟")) == ["弟", "兄"]


def test_find_by_reading_without_okurigana_dot_and_in_katakana(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM
) -> None:
    repo.add(make_kanji_with(user.id, "食", on=["ショク"], kun=["た.べる"]))
    repo.add(make_kanji_with(user.id, "会", on=["カイ"], kun=["あ.う"]))
    repo.add(make_kanji_with(user.id, "合", kun=["-あ.う"]))

    assert _found(repo, user, _search("taberu", "たべる", "タベル")) == ["食"]
    assert _found(repo, user, _search("kai", "かい", "カイ")) == ["会"]
    # Exact for both, so newest-first (same date: higher id first).
    assert _found(repo, user, _search("au", "あう", "アウ")) == ["合", "会"]


def test_find_ranks_exact_meaning_before_word_start(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM
) -> None:
    repo.add(make_kanji_with(user.id, "偶", meanings=[("same kind", "en")]))
    repo.add(make_kanji_with(user.id, "同", meanings=[("same", "en"), ("igual", "es")]))

    assert _found(repo, user, _search("same", meaning_lang="en")) == ["同", "偶"]
    assert _found(repo, user, _search("igual", meaning_lang="en")) == []
    assert _found(repo, user, _search("igual", meaning_lang="es")) == ["同"]


def test_find_out_of_a_collection(
    repo: SqlAlchemyPracticeKanjiRepository, user: UserORM, session: Session
) -> None:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    collection = collections.add(make_kanji_collection(user.id))
    collections.add_item(collection, repo.add(make_kanji_with(user.id, "兄")))
    repo.add(make_kanji_with(user.id, "弟"))

    assert _found(repo, user, _search("兄弟"), NotInCollection(collection)) == ["弟"]
