import pytest
from factories import sudachi
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import (
    CreateEntryCollection,
    CreateKanjiCollection,
    CreateOwnEntry,
    ImportEntry,
    ImportKanji,
    PublishEntryCollection,
    PublishKanjiCollection,
)
from shodoukan_practice.application.queries import (
    GetPublicEntryCollection,
    PreviewPublicEntryCollection,
    PreviewPublicKanjiCollection,
    SearchPublicEntryCollections,
    build_public_search,
)
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.dictionary import ShodoukanDictionaryGateway
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyKanjiCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
    SqlAlchemyPracticeKanjiRepository,
    SqlAlchemyPracticeSentenceRepository,
)


@pytest.fixture
def gateway(dictionary: Dictionary) -> ShodoukanDictionaryGateway:
    return ShodoukanDictionaryGateway(dictionary)


def test_build_public_search_trims_and_lowercases() -> None:
    assert build_public_search("  JLPT ", "all", "recent").text == "jlpt"
    assert build_public_search("   ", "mine", "popular").text is None


def test_search_get_and_preview_a_public_collection(
    session: Session,
    gateway: ShodoukanDictionaryGateway,
    user: UserORM,
    other_user: UserORM,
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    entries = SqlAlchemyPracticeEntryRepository(session)
    words = CreateEntryCollection(collections).execute(user.id, "Words", "N5")
    eat = ImportEntry(
        gateway,
        entries,
        collections,
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    ).execute(user.id, 1000001, [words.id or 0])
    eat.item.add_gloss(eat.item.senses[0].id or 0, "to scoff", "eng")
    entries.update(eat.item)
    CreateOwnEntry(entries, collections).execute(
        user.id, ["三匹"], ["さんびき"], "three animals", "eng", [words.id or 0]
    )
    PublishEntryCollection(
        collections, entries, SqlAlchemyPracticeSentenceRepository(session)
    ).execute(user.id, words.id or 0, False)

    page = SearchPublicEntryCollections(collections).execute(other_user.id, "n5")
    assert [s.collection.name for s in page.items] == ["Words"]
    assert page.total == 1
    summary = GetPublicEntryCollection(collections).execute(
        other_user.id, words.id or 0
    )
    assert (summary.owner_username, summary.item_count) == ("saul", 2)

    preview = PreviewPublicEntryCollection(collections, gateway).execute(
        other_user.id, words.id or 0, limit=10
    )
    assert preview.total == 2
    eat_copy, own = (p.entry for p in preview.items)
    assert eat_copy.user_id == other_user.id and eat_copy.id is None
    assert "to scoff" in [g.text for g in eat_copy.senses[0].glosses]
    assert own.is_own and [r.text for r in own.readings] == ["さんびき"]
    # Nothing was stored.
    assert entries.get_by_source_entry_id(1000001, other_user.id) is None


def test_preview_of_a_private_collection_is_not_found(
    session: Session, gateway: ShodoukanDictionaryGateway, user: UserORM
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    private = CreateEntryCollection(collections).execute(user.id, "private")
    with pytest.raises(EntityNotFoundError):
        PreviewPublicEntryCollection(collections, gateway).execute(
            user.id, private.id or 0
        )
    with pytest.raises(EntityNotFoundError):
        GetPublicEntryCollection(collections).execute(user.id, private.id or 0)


def test_preview_of_a_kanji_collection(
    session: Session,
    gateway: ShodoukanDictionaryGateway,
    user: UserORM,
    other_user: UserORM,
) -> None:
    collections = SqlAlchemyKanjiCollectionRepository(session)
    kanji = SqlAlchemyPracticeKanjiRepository(session)
    n4 = CreateKanjiCollection(collections).execute(user.id, "N4")
    eat = ImportKanji(gateway, kanji, collections).execute(user.id, "食", [n4.id or 0])
    eat.item.add_meaning("meal", "en")
    kanji.update(eat.item)
    PublishKanjiCollection(collections, kanji).execute(user.id, n4.id or 0, False)

    preview = PreviewPublicKanjiCollection(collections, gateway).execute(
        other_user.id, n4.id or 0
    )
    assert [k.literal for k in preview.items] == ["食"]
    assert "meal" in [m.text for m in preview.items[0].meanings]
