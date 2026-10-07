"""A saved exercise: which collections it draws from, its type and settings.

An exercise works on entries or on kanji, never both, like collections: the
subclass says which, and so which fields can be studied and which
collections it may use. Running it (sessions, questions, answers) is a
separate aggregate.

`settings` depends on the exercise type and is a union discriminated by
`type`. Card types share `CardSettings`: directions (fields shown → field
asked) and the fields on the back of the card. See
docs/practice/technical/exercises.md.
"""

from collections.abc import Sequence
from typing import Annotated, ClassVar, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .timestamped_entity import TimestampedEntity

EXERCISE_NAME_MAX_LENGTH = 100

ItemKind = Literal["entries", "kanji"]

# Every field an exercise can study. Which ones apply depends on the item
# kind: `ENTRY_FIELDS` / `KANJI_FIELDS`.
StudyField = Literal["writing", "reading", "meaning", "literal", "onyomi", "kunyomi"]

ENTRY_FIELDS: frozenset[StudyField] = frozenset({"writing", "reading", "meaning"})
KANJI_FIELDS: frozenset[StudyField] = frozenset(
    {"literal", "onyomi", "kunyomi", "meaning"}
)


class Direction(BaseModel):
    """Show the `prompt` fields, ask for the `answer` field."""

    model_config = ConfigDict(frozen=True)

    prompt: tuple[StudyField, ...] = Field(min_length=1)
    answer: StudyField

    @model_validator(mode="after")
    def _check(self) -> Self:
        if len(set(self.prompt)) != len(self.prompt):
            raise ValueError("a direction can't show the same field twice")
        if self.answer in self.prompt:
            raise ValueError("a direction can't ask for a field it shows")
        return self

    @property
    def fields(self) -> frozenset[StudyField]:
        return frozenset((*self.prompt, self.answer))


class CardSettings(BaseModel):
    """What every card exercise has: directions and the back of the card."""

    model_config = ConfigDict(frozen=True)

    directions: tuple[Direction, ...] = Field(min_length=1)
    # Shown on the back once answered, besides the prompt and the answer.
    back_fields: tuple[StudyField, ...] = ()

    @model_validator(mode="after")
    def _check_card(self) -> Self:
        keys = [(frozenset(d.prompt), d.answer) for d in self.directions]
        if len(set(keys)) != len(keys):
            raise ValueError("an exercise can't repeat a direction")
        if len(set(self.back_fields)) != len(self.back_fields):
            raise ValueError("a back field can't be repeated")
        return self

    @property
    def fields(self) -> frozenset[StudyField]:
        """Every field the settings use."""
        used: set[StudyField] = set(self.back_fields)
        for direction in self.directions:
            used |= direction.fields
        return frozenset(used)


class ChoiceCardSettings(CardSettings):
    """Pick the right answer among `option_count` options."""

    type: Literal["card.choice"] = "card.choice"
    option_count: int = Field(default=4, ge=2, le=8)
    # Where wrong options come from; "library" is planned.
    distractor_source: Literal["collection"] = "collection"


# What a handwriting card can ask to write: a kanji (`literal`), or a word's
# spelling (`writing`) or reading (`reading`), character by character. Which
# ones apply follows from the item kind's fields.
HANDWRITING_ANSWERS: frozenset[StudyField] = frozenset(
    {"literal", "writing", "reading"}
)


class HandwritingCardSettings(CardSettings):
    """Write the answer by hand: a kanji for kanji exercises (`literal`), a
    word's spelling or reading for entry exercises (`writing`, `reading`)."""

    type: Literal["card.handwriting"] = "card.handwriting"

    @model_validator(mode="after")
    def _check_answers(self) -> Self:
        if any(d.answer not in HANDWRITING_ANSWERS for d in self.directions):
            raise ValueError(
                "a handwriting card asks for a kanji (literal), or a word's "
                "writing or reading"
            )
        return self


# The settings of every exercise type, by `type`.
ExerciseSettings = Annotated[
    ChoiceCardSettings | HandwritingCardSettings, Field(discriminator="type")
]


class Exercise(TimestampedEntity):
    """Shared base; instantiate `EntryExercise` or `KanjiExercise`."""

    ITEM_KIND: ClassVar[ItemKind]
    FIELDS: ClassVar[frozenset[StudyField]]

    id: int | None
    user_id: UUID
    name: str = Field(min_length=1, max_length=EXERCISE_NAME_MAX_LENGTH)
    description: str | None = None
    # The collections it draws from, of the subclass's kind. Part of the
    # definition, so held here; it can end up empty when they're deleted,
    # and then the exercise can't be run until it gets one.
    collection_ids: tuple[int, ...] = ()
    settings: ExerciseSettings

    @model_validator(mode="after")
    def _check_fields(self) -> Self:
        foreign = self.settings.fields - self.FIELDS
        if foreign:
            raise ValueError(
                f"{', '.join(sorted(foreign))} can't be studied in "
                f"{self.ITEM_KIND} exercises"
            )
        return self

    @property
    def item_kind(self) -> ItemKind:
        return self.ITEM_KIND

    def rename(self, name: str) -> None:
        if name != self.name:
            self.name = name
            self.touch()

    def describe(self, description: str | None) -> None:
        if description != self.description:
            self.description = description
            self.touch()

    def configure(self, settings: ExerciseSettings) -> None:
        if settings != self.settings:
            self.settings = settings
            self.touch()

    def use_collections(self, collection_ids: Sequence[int]) -> None:
        """Draw from these collections, in this order (duplicates dropped)."""
        ids = tuple(dict.fromkeys(collection_ids))
        if ids != self.collection_ids:
            self.collection_ids = ids
            self.touch()


class EntryExercise(Exercise):
    """Studies `PracticeEntry` items from entry collections."""

    ITEM_KIND: ClassVar[ItemKind] = "entries"
    FIELDS: ClassVar[frozenset[StudyField]] = ENTRY_FIELDS


class KanjiExercise(Exercise):
    """Studies `PracticeKanji` items from kanji collections."""

    ITEM_KIND: ClassVar[ItemKind] = "kanji"
    FIELDS: ClassVar[frozenset[StudyField]] = KANJI_FIELDS
