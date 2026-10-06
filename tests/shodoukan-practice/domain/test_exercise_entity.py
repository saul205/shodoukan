import pytest
from factories import (
    NOW,
    USER_ID,
    choice_settings,
    handwriting_settings,
    make_entry_exercise,
)
from pydantic import ValidationError

from shodoukan_practice.domain.entities import (
    ChoiceCardSettings,
    Direction,
    EntryExercise,
    HandwritingCardSettings,
    KanjiExercise,
)


def test_direction_fields() -> None:
    direction = Direction(prompt=("literal", "meaning"), answer="kunyomi")
    assert direction.fields == {"literal", "meaning", "kunyomi"}


@pytest.mark.parametrize(
    ("prompt", "answer"),
    [
        ((), "reading"),  # nothing shown
        (("reading",), "reading"),  # asks for what it shows
        (("meaning", "meaning"), "reading"),  # same field twice
    ],
)
def test_invalid_directions(prompt: tuple[str, ...], answer: str) -> None:
    with pytest.raises(ValidationError):
        Direction.model_validate({"prompt": prompt, "answer": answer})


def test_settings_defaults_and_fields() -> None:
    settings = choice_settings(
        (("literal",), "kunyomi"), (("kunyomi",), "literal"), back_fields=["meaning"]
    )
    assert settings.type == "card.choice"
    assert settings.option_count == 4
    assert settings.distractor_source == "collection"
    assert settings.fields == {"literal", "kunyomi", "meaning"}


def test_settings_need_a_direction() -> None:
    with pytest.raises(ValidationError):
        ChoiceCardSettings(directions=())


def test_settings_reject_repeated_directions() -> None:
    # The prompt order doesn't make a direction different.
    with pytest.raises(ValidationError, match="repeat a direction"):
        choice_settings(
            (("reading", "meaning"), "writing"), (("meaning", "reading"), "writing")
        )


def test_settings_reject_repeated_back_fields() -> None:
    with pytest.raises(ValidationError):
        choice_settings((("writing",), "meaning"), back_fields=["reading", "reading"])


@pytest.mark.parametrize("option_count", [1, 9])
def test_settings_bound_the_options(option_count: int) -> None:
    with pytest.raises(ValidationError):
        choice_settings((("writing",), "meaning"), option_count=option_count)


def test_old_settings_with_question_count_still_load() -> None:
    settings = choice_settings((("writing",), "meaning"), question_count=10)
    assert "question_count" not in settings.model_dump()


def test_item_kind_comes_from_the_subclass() -> None:
    assert make_entry_exercise(USER_ID).item_kind == "entries"
    exercise = KanjiExercise(
        id=None,
        user_id=USER_ID,
        name="k",
        settings=choice_settings((("literal",), "onyomi")),
    )
    assert exercise.item_kind == "kanji"


def test_fields_must_fit_the_item_kind() -> None:
    with pytest.raises(ValidationError, match="onyomi can't be studied in entries"):
        EntryExercise(
            id=None,
            user_id=USER_ID,
            name="x",
            settings=choice_settings((("writing",), "onyomi")),
        )
    with pytest.raises(ValidationError, match="reading"):
        KanjiExercise(
            id=None,
            user_id=USER_ID,
            name="x",
            settings=choice_settings((("literal",), "onyomi"), back_fields=["reading"]),
        )


@pytest.mark.parametrize("name", ["", "x" * 101])
def test_name_length(name: str) -> None:
    with pytest.raises(ValidationError):
        make_entry_exercise(USER_ID, name=name)


def test_methods_touch_only_on_change() -> None:
    exercise = make_entry_exercise(USER_ID, (1,))
    exercise.rename("Verbs")
    exercise.describe(None)
    exercise.use_collections([1])
    exercise.configure(exercise.settings.model_copy())
    assert exercise.updated_at == NOW

    exercise.rename("Godan")
    assert exercise.name == "Godan"
    assert exercise.updated_at > NOW


def test_use_collections_keeps_order_and_drops_duplicates() -> None:
    exercise = make_entry_exercise(USER_ID, (1,))
    exercise.use_collections([3, 1, 3])
    assert exercise.collection_ids == (3, 1)
    assert exercise.updated_at > NOW


def test_configure_checks_the_item_kind() -> None:
    exercise = make_entry_exercise(USER_ID)
    with pytest.raises(ValidationError):
        exercise.configure(choice_settings((("literal",), "onyomi")))


def test_configure_replaces_the_settings() -> None:
    exercise = make_entry_exercise(USER_ID)
    settings = choice_settings((("reading",), "meaning"), option_count=6)
    exercise.configure(settings)
    assert exercise.settings == settings
    assert exercise.updated_at > NOW


def test_handwriting_always_asks_for_the_kanji() -> None:
    settings = handwriting_settings(("meaning",), ("onyomi", "kunyomi"))
    assert settings.type == "card.handwriting"

    with pytest.raises(ValidationError, match="asks for the kanji"):
        HandwritingCardSettings.model_validate(
            {"directions": [{"prompt": ["literal"], "answer": "meaning"}]}
        )


def test_an_entry_exercise_cant_be_drawn() -> None:
    exercise = make_entry_exercise(USER_ID)

    with pytest.raises(ValidationError):
        EntryExercise.model_validate(
            {**exercise.model_dump(), "settings": handwriting_settings(("meaning",))}
        )
