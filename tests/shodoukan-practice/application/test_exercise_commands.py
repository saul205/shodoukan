import pytest
from factories import NOW, choice_settings, make_entry_collection, make_kanji_collection
from pydantic import ValidationError
from sqlalchemy.orm import Session

from shodoukan_practice.application.commands import (
    CreateExercise,
    DeleteExercise,
    UpdateExercise,
)
from shodoukan_practice.domain.entities import (
    EntryCollection,
    EntryExercise,
    Exercise,
    KanjiCollection,
    KanjiExercise,
)
from shodoukan_practice.domain.exceptions import EntityNotFoundError
from shodoukan_practice.infrastructure.db.orm import UserORM
from shodoukan_practice.infrastructure.repositories import (
    SqlAlchemyEntryCollectionRepository,
    SqlAlchemyExerciseRepository,
    SqlAlchemyKanjiCollectionRepository,
)

WORDS = choice_settings((("meaning",), "writing"), back_fields=["reading"])
KANJI = choice_settings((("literal",), "kunyomi"), (("kunyomi",), "literal"))


@pytest.fixture
def exercises(session: Session) -> SqlAlchemyExerciseRepository:
    return SqlAlchemyExerciseRepository(session)


@pytest.fixture
def create(session: Session, exercises: SqlAlchemyExerciseRepository) -> CreateExercise:
    return CreateExercise(
        exercises,
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


@pytest.fixture
def update(session: Session, exercises: SqlAlchemyExerciseRepository) -> UpdateExercise:
    return UpdateExercise(
        exercises,
        SqlAlchemyEntryCollectionRepository(session),
        SqlAlchemyKanjiCollectionRepository(session),
    )


@pytest.fixture
def verbs(session: Session, user: UserORM) -> EntryCollection:
    return SqlAlchemyEntryCollectionRepository(session).add(
        make_entry_collection(user.id, "verbs")
    )


@pytest.fixture
def n5(session: Session, user: UserORM) -> KanjiCollection:
    return SqlAlchemyKanjiCollectionRepository(session).add(
        make_kanji_collection(user.id, "N5")
    )


@pytest.fixture
def words(create: CreateExercise, user: UserORM, verbs: EntryCollection) -> Exercise:
    assert verbs.id is not None
    return create.execute(user.id, "entries", "Verbs", None, [verbs.id], WORDS)


def test_create_entry_and_kanji_exercises(
    create: CreateExercise,
    exercises: SqlAlchemyExerciseRepository,
    user: UserORM,
    verbs: EntryCollection,
    n5: KanjiCollection,
) -> None:
    assert verbs.id is not None and n5.id is not None
    words = create.execute(
        user.id, "entries", "Verbs", "Godan", [verbs.id, verbs.id], WORDS
    )
    kanji = create.execute(user.id, "kanji", "N5", None, [n5.id], KANJI)

    assert isinstance(words, EntryExercise)
    assert words.collection_ids == (verbs.id,)  # duplicates dropped
    assert words.description == "Godan"
    assert isinstance(kanji, KanjiExercise)
    assert kanji.id is not None
    assert exercises.get(kanji.id, user.id) == kanji


def test_create_rejects_collections_that_arent_usable(
    create: CreateExercise,
    user: UserORM,
    other_user: UserORM,
    session: Session,
    n5: KanjiCollection,
) -> None:
    foreign = SqlAlchemyEntryCollectionRepository(session).add(
        make_entry_collection(other_user.id, "theirs")
    )
    assert foreign.id is not None and n5.id is not None
    with pytest.raises(EntityNotFoundError):
        create.execute(user.id, "entries", "x", None, [foreign.id], WORDS)
    # A kanji collection's id means nothing for an entry exercise.
    with pytest.raises(EntityNotFoundError):
        create.execute(user.id, "entries", "x", None, [n5.id + 100], WORDS)


def test_create_rejects_fields_of_the_other_kind(
    create: CreateExercise, user: UserORM, verbs: EntryCollection
) -> None:
    assert verbs.id is not None
    with pytest.raises(ValidationError):
        create.execute(user.id, "entries", "x", None, [verbs.id], KANJI)


def test_update_replaces_everything_but_the_kind(
    update: UpdateExercise,
    session: Session,
    user: UserORM,
    words: Exercise,
    verbs: EntryCollection,
) -> None:
    nouns = SqlAlchemyEntryCollectionRepository(session).add(
        make_entry_collection(user.id, "nouns")
    )
    assert words.id is not None and nouns.id is not None and verbs.id is not None
    settings = choice_settings((("reading",), "meaning"), option_count=6)

    updated = update.execute(
        user.id, words.id, "Words", "All", [nouns.id, verbs.id], settings
    )

    assert isinstance(updated, EntryExercise)
    assert updated.name == "Words"
    assert updated.description == "All"
    assert updated.collection_ids == (nouns.id, verbs.id)
    assert updated.settings == settings
    assert updated.updated_at > NOW


def test_update_without_changes_keeps_updated_at(
    update: UpdateExercise, user: UserORM, words: Exercise
) -> None:
    assert words.id is not None
    same = update.execute(
        user.id, words.id, words.name, None, list(words.collection_ids), WORDS
    )
    assert same.updated_at == words.updated_at


def test_update_checks_the_exercise_and_its_kind(
    update: UpdateExercise,
    user: UserORM,
    other_user: UserORM,
    words: Exercise,
    n5: KanjiCollection,
) -> None:
    assert words.id is not None and n5.id is not None
    with pytest.raises(EntityNotFoundError):
        update.execute(other_user.id, words.id, "x", None, [1], WORDS)
    with pytest.raises(ValidationError):
        update.execute(user.id, words.id, "x", None, list(words.collection_ids), KANJI)


def test_delete(
    exercises: SqlAlchemyExerciseRepository,
    user: UserORM,
    other_user: UserORM,
    words: Exercise,
) -> None:
    assert words.id is not None
    delete = DeleteExercise(exercises)
    with pytest.raises(EntityNotFoundError):
        delete.execute(other_user.id, words.id)

    delete.execute(user.id, words.id)

    assert exercises.get(words.id, user.id) is None
    with pytest.raises(EntityNotFoundError):
        delete.execute(user.id, words.id)
