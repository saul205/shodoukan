import pytest
from factories import NOW, make_entry, make_kanji, sudachi
from sqlalchemy.orm import Session

from shodoukan import Dictionary
from shodoukan_practice.application.commands import (
    AddEntryToCollection,
    AddKanjiToCollection,
    AddSentence,
    CreateEntryCollection,
    CreateKanjiCollection,
    CreateOwnEntry,
    DeleteEntryCollection,
    DeleteKanjiCollection,
    ImportEntry,
    ImportEntryCollection,
    ImportKanji,
    ImportKanjiCollection,
    RemoveEntryFromCollection,
    RemoveKanjiFromCollection,
    UpdateEntryCollection,
    UpdateKanjiCollection,
)
from shodoukan_practice.application.queries import (
    ExportEntryCollection,
    ExportKanjiCollection,
)
from shodoukan_practice.domain.entities import (
    FILE,
    EntryCollection,
    KanjiCollection,
    PracticeEntry,
    PracticeKanji,
    SharedEntry,
    SharedEntryCollection,
)
from shodoukan_practice.domain.exceptions import (
    CollectionNameTakenError,
    EntityNotFoundError,
)
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
def collections(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def kanji_collections(session: Session) -> SqlAlchemyKanjiCollectionRepository:
    return SqlAlchemyKanjiCollectionRepository(session)


@pytest.fixture
def entries(session: Session) -> SqlAlchemyPracticeEntryRepository:
    return SqlAlchemyPracticeEntryRepository(session)


@pytest.fixture
def kanji(session: Session) -> SqlAlchemyPracticeKanjiRepository:
    return SqlAlchemyPracticeKanjiRepository(session)


@pytest.fixture
def verbs(
    collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> EntryCollection:
    return CreateEntryCollection(collections).execute(user.id, "verbs")


@pytest.fixture
def entry(entries: SqlAlchemyPracticeEntryRepository, user: UserORM) -> PracticeEntry:
    return entries.add(make_entry(user.id))


def _id(item: EntryCollection | KanjiCollection | PracticeEntry | PracticeKanji) -> int:
    assert item.id is not None
    return item.id


def test_create_stores_an_empty_collection(
    collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    created = CreateEntryCollection(collections).execute(
        user.id, "verbs", "Godan and ichidan"
    )

    assert created.description == "Godan and ichidan"
    assert collections.get(_id(created), user.id) == created
    assert collections.item_ids([created]) == set()


def test_create_with_a_taken_name_fails(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    with pytest.raises(CollectionNameTakenError):
        CreateEntryCollection(collections).execute(user.id, "verbs")


def test_entry_and_kanji_collections_may_share_a_name(
    kanji_collections: SqlAlchemyKanjiCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    created = CreateKanjiCollection(kanji_collections).execute(user.id, "verbs")
    assert created.name == "verbs"


def test_update_replaces_name_and_description(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    updated = UpdateEntryCollection(collections).execute(
        user.id, _id(verbs), "godan", "う-verbs"
    )

    assert (updated.name, updated.description) == ("godan", "う-verbs")
    assert updated.updated_at > verbs.updated_at
    assert collections.get(_id(verbs), user.id) == updated


def test_update_without_changes_keeps_updated_at(
    collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> None:
    created = collections.add(
        EntryCollection(
            id=None, user_id=user.id, name="verbs", created_at=NOW, updated_at=NOW
        )
    )
    updated = UpdateEntryCollection(collections).execute(
        user.id, _id(created), "verbs", None
    )
    assert updated.updated_at == NOW


def test_update_of_another_users_collection_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    with pytest.raises(EntityNotFoundError):
        UpdateEntryCollection(collections).execute(
            other_user.id, _id(verbs), "mine", None
        )


def test_update_to_a_taken_name_fails(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> None:
    nouns = CreateEntryCollection(collections).execute(user.id, "nouns")
    with pytest.raises(CollectionNameTakenError):
        UpdateEntryCollection(collections).execute(user.id, _id(nouns), "verbs", None)


def test_delete_keeps_the_items(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    entry: PracticeEntry,
    user: UserORM,
) -> None:
    AddEntryToCollection(collections, entries).execute(user.id, _id(verbs), _id(entry))
    DeleteEntryCollection(collections).execute(user.id, _id(verbs))

    assert collections.get(_id(verbs), user.id) is None
    assert entries.get(_id(entry), user.id) == entry


def test_delete_of_another_users_collection_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    with pytest.raises(EntityNotFoundError):
        DeleteEntryCollection(collections).execute(other_user.id, _id(verbs))


def test_add_and_remove_entry_are_idempotent(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    entry: PracticeEntry,
    user: UserORM,
) -> None:
    add = AddEntryToCollection(collections, entries)
    remove = RemoveEntryFromCollection(collections, entries)

    add.execute(user.id, _id(verbs), _id(entry))
    add.execute(user.id, _id(verbs), _id(entry))
    assert collections.item_ids([verbs]) == {_id(entry)}

    remove.execute(user.id, _id(verbs), _id(entry))
    remove.execute(user.id, _id(verbs), _id(entry))
    assert collections.item_ids([verbs]) == set()


def test_add_another_users_entry_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    theirs = entries.add(make_entry(other_user.id))
    with pytest.raises(EntityNotFoundError):
        AddEntryToCollection(collections, entries).execute(
            user.id, _id(verbs), _id(theirs)
        )


def test_add_to_another_users_collection_is_not_found(
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    other_user: UserORM,
) -> None:
    theirs = entries.add(make_entry(other_user.id))
    with pytest.raises(EntityNotFoundError):
        AddEntryToCollection(collections, entries).execute(
            other_user.id, _id(verbs), _id(theirs)
        )


def test_kanji_collection_lifecycle(
    kanji_collections: SqlAlchemyKanjiCollectionRepository,
    kanji: SqlAlchemyPracticeKanjiRepository,
    user: UserORM,
) -> None:
    item = kanji.add(make_kanji(user.id))
    n5 = CreateKanjiCollection(kanji_collections).execute(user.id, "N5")

    AddKanjiToCollection(kanji_collections, kanji).execute(user.id, _id(n5), _id(item))
    assert kanji_collections.item_ids([n5]) == {_id(item)}

    renamed = UpdateKanjiCollection(kanji_collections).execute(
        user.id, _id(n5), "JLPT N5", None
    )
    assert renamed.name == "JLPT N5"

    RemoveKanjiFromCollection(kanji_collections, kanji).execute(
        user.id, _id(n5), _id(item)
    )
    assert kanji_collections.item_ids([n5]) == set()

    DeleteKanjiCollection(kanji_collections).execute(user.id, _id(n5))
    assert kanji_collections.get(_id(n5), user.id) is None
    with pytest.raises(EntityNotFoundError):
        AddKanjiToCollection(kanji_collections, kanji).execute(
            user.id, _id(n5), _id(item)
        )


# --- Export and import ---


@pytest.fixture
def import_entries(session: Session, dictionary: Dictionary) -> ImportEntryCollection:
    return ImportEntryCollection(
        ShodoukanDictionaryGateway(dictionary),
        SqlAlchemyPracticeEntryRepository(session),
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyPracticeSentenceRepository(session),
        sudachi(),
    )


@pytest.fixture
def import_kanji_collection(
    session: Session, dictionary: Dictionary
) -> ImportKanjiCollection:
    return ImportKanjiCollection(
        ShodoukanDictionaryGateway(dictionary),
        SqlAlchemyPracticeKanjiRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


@pytest.fixture
def exported_verbs(
    session: Session,
    dictionary: Dictionary,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    user: UserORM,
) -> SharedEntryCollection:
    """The user's "verbs": 食べる with their own meaning, note and a hidden
    spelling, and a word of their own."""
    gateway = ShodoukanDictionaryGateway(dictionary)
    eat = (
        ImportEntry(
            gateway,
            entries,
            collections,
            SqlAlchemyPracticeSentenceRepository(session),
            sudachi(),
        )
        .execute(user.id, 1000001)
        .item
    )
    assert eat.id is not None
    eat.add_gloss(eat.senses[0].id or 0, "to scoff", "eng")
    eat.set_notes("my note")
    eat.set_enabled("kanji_readings", eat.kanji_readings[0].id or 0, False)
    entries.update(eat)
    collections.add_item(verbs, eat)
    CreateOwnEntry(entries, collections).execute(
        user.id, ["三匹"], ["さんびき"], "three animals", "eng", [verbs.id or 0]
    )
    session.expunge_all()
    return ExportEntryCollection(
        collections, entries, SqlAlchemyPracticeSentenceRepository(session)
    ).execute(user.id, verbs.id or 0)


def test_import_copies_a_collection_into_another_library(
    import_entries: ImportEntryCollection,
    collections: SqlAlchemyEntryCollectionRepository,
    exported_verbs: SharedEntryCollection,
    entries: SqlAlchemyPracticeEntryRepository,
    other_user: UserORM,
) -> None:
    result = import_entries.execute(other_user.id, exported_verbs)

    assert (result.created, result.existing, result.missing) == (2, 0, [])
    assert result.collection.name == "verbs"
    # From a file: no source, so never updated, and its parts are pinned.
    assert result.collection.source_collection_id is None
    assert collections.source_item_ids(result.collection) == set()
    eat = entries.get_by_source_entry_id(1000001, other_user.id)
    assert eat is not None
    assert eat.notes == "my note"
    assert eat.kanji_readings[0].enabled is False
    assert [g.text for g in eat.senses[0].glosses][-1] == "to scoff"
    assert eat.senses[0].glosses[-1].source_collection_ids == [FILE]
    own = entries.find_own_by_identity(
        [exported_verbs.items[1].identity or 0], other_user.id
    )
    assert [r.text for r in own[0].readings] == ["さんびき"]


def test_importing_again_duplicates_nothing(
    import_entries: ImportEntryCollection,
    exported_verbs: SharedEntryCollection,
    entries: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
) -> None:
    eat_before = entries.get_by_source_entry_id(1000001, user.id)

    result = import_entries.execute(user.id, exported_verbs)

    assert (result.created, result.existing) == (0, 2)
    assert result.collection.name == "verbs (2)"
    assert entries.get_by_source_entry_id(1000001, user.id) == eat_before
    own = entries.find_own_by_identity([exported_verbs.items[1].identity or 0], user.id)
    assert len(own) == 1


def test_import_leaves_out_what_the_dictionary_no_longer_has(
    import_entries: ImportEntryCollection,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    user: UserORM,
) -> None:
    shared = SharedEntryCollection(
        name="old",
        items=[SharedEntry(source_entry_id=999), SharedEntry(source_entry_id=1000002)],
    )
    result = import_entries.execute(user.id, shared)

    assert (result.created, result.missing) == (1, [999])
    assert collections.item_ids([result.collection]) == {
        entries.practice_ids_by_source_entry_id([1000002], user.id)[1000002]
    }


def test_import_kanji_collection_round_trip(
    session: Session,
    dictionary: Dictionary,
    import_kanji_collection: ImportKanjiCollection,
    kanji_collections: SqlAlchemyKanjiCollectionRepository,
    kanji: SqlAlchemyPracticeKanjiRepository,
    user: UserORM,
    other_user: UserORM,
) -> None:
    gateway = ShodoukanDictionaryGateway(dictionary)
    mine = CreateKanjiCollection(kanji_collections).execute(user.id, "N4")
    eat = (
        ImportKanji(gateway, kanji, kanji_collections)
        .execute(user.id, "食", [mine.id or 0])
        .item
    )
    eat.add_meaning("meal", "en")
    kanji.update(eat)
    session.expunge_all()
    shared = ExportKanjiCollection(kanji_collections, kanji).execute(
        user.id, mine.id or 0
    )

    result = import_kanji_collection.execute(other_user.id, shared)
    again = import_kanji_collection.execute(other_user.id, shared)

    assert (result.created, again.existing) == (1, 1)
    copy = kanji.get_by_literal("食", other_user.id)
    assert copy is not None
    assert [m.text for m in copy.meanings].count("meal") == 1


def test_a_words_sentences_travel_with_the_collection(
    session: Session,
    dictionary: Dictionary,
    import_entries: ImportEntryCollection,
    collections: SqlAlchemyEntryCollectionRepository,
    entries: SqlAlchemyPracticeEntryRepository,
    verbs: EntryCollection,
    user: UserORM,
    other_user: UserORM,
) -> None:
    sentences = SqlAlchemyPracticeSentenceRepository(session)
    eat = (
        ImportEntry(
            ShodoukanDictionaryGateway(dictionary),
            entries,
            collections,
            sentences,
            sudachi(),
        )
        .execute(user.id, 1000001, [verbs.id or 0])
        .item
    )
    mine = AddSentence(sentences, entries, sudachi()).execute(
        user.id, "昨日パンを食べた。", "I ate bread.", "eng", entry_id=eat.id
    )
    shared = ExportEntryCollection(collections, entries, sentences).execute(
        user.id, verbs.id or 0
    )
    [example] = shared.items[0].senses[0].examples
    assert example.word is not None and example.word.lemma == "食べる"

    import_entries.execute(other_user.id, shared)
    import_entries.execute(other_user.id, shared)  # again: nothing twice

    theirs = entries.get_by_source_entry_id(1000001, other_user.id)
    assert theirs is not None
    [copy] = sentences.for_entry(theirs.id or 0, other_user.id)
    [word] = copy.words
    assert (copy.text, copy.origin, copy.original_id) == (mine.text, "added", mine.id)
    assert copy.source_collection_ids == [FILE]
    assert copy.surface(word) == "食べた"
    assert (word.lemma, word.reading, word.sense_id) == (
        "食べる",
        "たべた",
        theirs.senses[0].id,
    )
