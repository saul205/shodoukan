import pytest
from factories import (
    choice_settings,
    make_entry_collection,
    make_entry_exercise,
    make_kanji_collection,
    make_kanji_exercise,
)
from sqlalchemy.orm import Session

from shodoukan_practice.domain.entities import EntryCollection, KanjiCollection
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyExerciseRepository,
    SqlAlchemyKanjiCollectionRepository,
)


@pytest.fixture
def repo(session: Session) -> SqlAlchemyExerciseRepository:
    return SqlAlchemyExerciseRepository(session)


@pytest.fixture
def entry_collections(session: Session) -> SqlAlchemyEntryCollectionRepository:
    return SqlAlchemyEntryCollectionRepository(session)


@pytest.fixture
def verbs(
    entry_collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> EntryCollection:
    return entry_collections.add(make_entry_collection(user.id, "verbs"))


@pytest.fixture
def nouns(
    entry_collections: SqlAlchemyEntryCollectionRepository, user: UserORM
) -> EntryCollection:
    return entry_collections.add(make_entry_collection(user.id, "nouns"))


@pytest.fixture
def n5(session: Session, user: UserORM) -> KanjiCollection:
    return SqlAlchemyKanjiCollectionRepository(session).add(
        make_kanji_collection(user.id, "N5")
    )


def _ids(*collections: EntryCollection | KanjiCollection) -> tuple[int, ...]:
    return tuple(c.id for c in collections if c.id is not None)


def test_add_and_get(
    repo: SqlAlchemyExerciseRepository,
    user: UserORM,
    verbs: EntryCollection,
    nouns: EntryCollection,
    n5: KanjiCollection,
) -> None:
    words = repo.add(make_entry_exercise(user.id, _ids(nouns, verbs)))
    kanji = repo.add(make_kanji_exercise(user.id, _ids(n5)))

    assert words.id is not None
    assert repo.get(words.id, user.id) == words
    assert words.collection_ids == _ids(nouns, verbs)
    assert kanji.id is not None
    assert repo.get(kanji.id, user.id) == kanji


def test_get_is_scoped_to_the_user(
    repo: SqlAlchemyExerciseRepository, user: UserORM, other_user: UserORM
) -> None:
    exercise = repo.add(make_entry_exercise(user.id))
    assert exercise.id is not None
    assert repo.get(exercise.id, other_user.id) is None
    assert repo.get(exercise.id + 1, user.id) is None


def test_list_for_user_is_by_name(
    repo: SqlAlchemyExerciseRepository, user: UserORM, other_user: UserORM
) -> None:
    repo.add(make_entry_exercise(user.id, name="b"))
    repo.add(make_kanji_exercise(user.id, name="a"))
    repo.add(make_entry_exercise(other_user.id, name="c"))

    assert [e.name for e in repo.list_for_user(user.id)] == ["a", "b"]


def test_update_replaces_fields_and_collections(
    repo: SqlAlchemyExerciseRepository,
    user: UserORM,
    verbs: EntryCollection,
    nouns: EntryCollection,
) -> None:
    exercise = repo.add(make_entry_exercise(user.id, _ids(verbs)))
    exercise.rename("Words")
    exercise.use_collections(_ids(nouns, verbs))
    exercise.configure(choice_settings((("reading",), "meaning"), option_count=6))

    updated = repo.update(exercise)

    assert exercise.id is not None
    assert repo.get(exercise.id, user.id) == updated == exercise

    exercise.use_collections(_ids(nouns))
    assert repo.update(exercise).collection_ids == _ids(nouns)


def test_update_of_a_missing_or_foreign_exercise(
    repo: SqlAlchemyExerciseRepository, user: UserORM, other_user: UserORM
) -> None:
    with pytest.raises(EntityNotFoundError):
        repo.update(make_entry_exercise(user.id))  # never stored

    exercise = repo.add(make_entry_exercise(user.id))
    stolen = exercise.model_copy(update={"user_id": other_user.id})
    with pytest.raises(EntityNotFoundError):
        repo.update(stolen)
    with pytest.raises(EntityNotFoundError):
        repo.delete(stolen)


def test_delete_keeps_the_collections(
    repo: SqlAlchemyExerciseRepository,
    entry_collections: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    verbs: EntryCollection,
) -> None:
    exercise = repo.add(make_entry_exercise(user.id, _ids(verbs)))
    repo.delete(exercise)

    assert exercise.id is not None
    assert repo.get(exercise.id, user.id) is None
    assert entry_collections.list_for_user(user.id) == [verbs]


def test_deleting_a_collection_removes_it_from_exercises(
    session: Session,
    repo: SqlAlchemyExerciseRepository,
    entry_collections: SqlAlchemyEntryCollectionRepository,
    user: UserORM,
    verbs: EntryCollection,
    nouns: EntryCollection,
) -> None:
    exercise = repo.add(make_entry_exercise(user.id, _ids(verbs, nouns)))
    entry_collections.delete(verbs)
    session.expire_all()

    assert exercise.id is not None
    stored = repo.get(exercise.id, user.id)
    assert stored is not None
    assert stored.collection_ids == _ids(nouns)

    entry_collections.delete(nouns)
    session.expire_all()
    stored = repo.get(exercise.id, user.id)
    assert stored is not None
    assert stored.collection_ids == ()  # kept, but can't run
