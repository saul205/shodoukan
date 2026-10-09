import pytest
from factories import make_entry, make_entry_collection
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import (
    AddEntryExample,
    AddEntryGloss,
    AddEntryReading,
    AddEntrySense,
    AddEntrySpelling,
    EditEntryExample,
    EditEntryGloss,
    RemoveEntryExample,
    RemoveEntryFromLibrary,
    RemoveEntryGloss,
    RemoveEntryReading,
    RemoveEntrySense,
    RemoveEntrySpelling,
    SetEntryActive,
    SetEntryNotes,
    SetEntryPartEnabled,
    SetSenseNotes,
)
from shodoukan_practice.domain.entities import PracticeEntry
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    OriginalDataError,
)
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyPracticeEntryRepository,
)


@pytest.fixture
def entries(session: Session) -> SqlAlchemyPracticeEntryRepository:
    return SqlAlchemyPracticeEntryRepository(session)


@pytest.fixture
def entry(entries: SqlAlchemyPracticeEntryRepository, user: UserORM) -> PracticeEntry:
    return entries.add(make_entry(user.id))


def _ids(entry: PracticeEntry) -> tuple[int, int, int]:
    """The entry, its first sense and that sense's first (imported) gloss."""
    sense = entry.senses[0]
    assert entry.id and sense.id and sense.glosses[0].id
    return entry.id, sense.id, sense.glosses[0].id


def test_notes_are_stored(
    entries: SqlAlchemyPracticeEntryRepository, entry: PracticeEntry, user: UserORM
) -> None:
    entry_id, sense_id, _ = _ids(entry)

    SetEntryNotes(entries).execute(user.id, entry_id, "ichidan")
    result = SetSenseNotes(entries).execute(user.id, entry_id, sense_id, "casual")

    assert (result.notes, result.senses[0].notes) == ("ichidan", "casual")
    assert entries.get(entry_id, user.id) == result


def test_set_active_and_enabled(
    entries: SqlAlchemyPracticeEntryRepository, entry: PracticeEntry, user: UserORM
) -> None:
    entry_id, _, gloss_id = _ids(entry)

    inactive = SetEntryActive(entries).execute(user.id, entry_id, False)
    hidden = SetEntryPartEnabled(entries).execute(
        user.id, entry_id, "glosses", gloss_id, False
    )

    assert inactive.is_active is False
    assert hidden.senses[0].glosses[0].enabled is False
    assert SetEntryActive(entries).execute(user.id, entry_id, True).is_active


def test_own_meanings_lifecycle(
    entries: SqlAlchemyPracticeEntryRepository, entry: PracticeEntry, user: UserORM
) -> None:
    entry_id, sense_id, _ = _ids(entry)

    added = AddEntryGloss(entries).execute(user.id, entry_id, sense_id, "scoff", "eng")
    gloss = added.senses[0].glosses[-1]
    assert gloss.id is not None and gloss.origin == "added"

    edited = EditEntryGloss(entries).execute(user.id, entry_id, gloss.id, "gobble")
    assert edited.senses[0].glosses[-1].text == "gobble"

    removed = RemoveEntryGloss(entries).execute(user.id, entry_id, gloss.id)
    assert [g.origin for g in removed.senses[0].glosses] == ["imported", "imported"]


def test_own_senses_lifecycle(
    entries: SqlAlchemyPracticeEntryRepository, entry: PracticeEntry, user: UserORM
) -> None:
    entry_id, sense_id, _ = _ids(entry)

    added = AddEntrySense(entries).execute(user.id, entry_id, "to dine", "eng")
    sense = added.senses[-1]
    assert sense.id is not None and sense.origin == "added"
    assert sense.glosses[0].id is not None
    assert entries.get(entry_id, user.id) == added

    hidden = SetEntryPartEnabled(entries).execute(
        user.id, entry_id, "senses", sense_id, False
    )
    assert hidden.senses[0].enabled is False

    removed = RemoveEntrySense(entries).execute(user.id, entry_id, sense.id)
    assert [s.id for s in removed.senses] == [sense_id]
    with pytest.raises(OriginalDataError):
        RemoveEntrySense(entries).execute(user.id, entry_id, sense_id)


def test_own_examples_lifecycle(
    entries: SqlAlchemyPracticeEntryRepository, entry: PracticeEntry, user: UserORM
) -> None:
    entry_id, sense_id, _ = _ids(entry)

    added = AddEntryExample(entries).execute(
        user.id, entry_id, sense_id, "朝ご飯を食べる。", "I eat breakfast.", "eng"
    )
    example = added.senses[0].examples[-1]
    assert example.id is not None and example.origin == "added"
    assert entries.get(entry_id, user.id) == added

    edited = EditEntryExample(entries).execute(
        user.id, entry_id, example.id, "朝ご飯を食べた。", None, "eng"
    )
    assert [s.text for s in edited.senses[0].examples[-1].sentences] == [
        "朝ご飯を食べた。"
    ]

    removed = RemoveEntryExample(entries).execute(user.id, entry_id, example.id)
    assert all(e.origin == "imported" for e in removed.senses[0].examples)
    imported = removed.senses[0].examples[0].id
    assert imported is not None
    with pytest.raises(OriginalDataError):
        RemoveEntryExample(entries).execute(user.id, entry_id, imported)


def test_own_spellings_and_readings_lifecycle(
    entries: SqlAlchemyPracticeEntryRepository, entry: PracticeEntry, user: UserORM
) -> None:
    entry_id = _ids(entry)[0]

    AddEntrySpelling(entries).execute(user.id, entry_id, "喰べる")
    added = AddEntryReading(entries).execute(user.id, entry_id, "くう")
    spelling, reading = added.kanji_readings[-1], added.readings[-1]
    assert spelling.id is not None and reading.id is not None
    assert (spelling.origin, reading.origin) == ("added", "added")
    assert entries.get(entry_id, user.id) == added

    RemoveEntrySpelling(entries).execute(user.id, entry_id, spelling.id)
    removed = RemoveEntryReading(entries).execute(user.id, entry_id, reading.id)
    assert all(k.origin == "imported" for k in removed.kanji_readings)
    assert all(r.origin == "imported" for r in removed.readings)


def test_dictionary_meanings_cant_be_edited_or_removed(
    entries: SqlAlchemyPracticeEntryRepository, entry: PracticeEntry, user: UserORM
) -> None:
    entry_id, _, gloss_id = _ids(entry)
    with pytest.raises(OriginalDataError):
        EditEntryGloss(entries).execute(user.id, entry_id, gloss_id, "x")
    with pytest.raises(OriginalDataError):
        RemoveEntryGloss(entries).execute(user.id, entry_id, gloss_id)


def test_another_users_entry_is_not_found(
    entries: SqlAlchemyPracticeEntryRepository,
    entry: PracticeEntry,
    other_user: UserORM,
) -> None:
    entry_id, sense_id, _ = _ids(entry)
    with pytest.raises(EntityNotFoundError):
        SetEntryNotes(entries).execute(other_user.id, entry_id, "mine")
    with pytest.raises(EntityNotFoundError):
        AddEntryGloss(entries).execute(other_user.id, entry_id, sense_id, "x", "eng")
    with pytest.raises(EntityNotFoundError):
        RemoveEntryFromLibrary(entries).execute(other_user.id, entry_id)


def test_remove_from_library_leaves_collections(
    entries: SqlAlchemyPracticeEntryRepository,
    entry: PracticeEntry,
    user: UserORM,
    session: Session,
) -> None:
    collections = SqlAlchemyEntryCollectionRepository(session)
    verbs = collections.add(make_entry_collection(user.id))
    collections.add_item(verbs, entry)
    entry_id, _, _ = _ids(entry)

    RemoveEntryFromLibrary(entries).execute(user.id, entry_id)

    assert entries.get(entry_id, user.id) is None
    assert collections.item_ids([verbs]) == set()
    assert collections.list_for_user(user.id) == [verbs]
