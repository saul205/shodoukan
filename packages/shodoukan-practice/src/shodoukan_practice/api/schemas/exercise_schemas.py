"""Request and response models for saved exercises.

`settings` is the domain's settings union as is: the API contract is the
JSON shape of `ChoiceCardSettings` (and later types), keyed by `type`.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from ...domain.entities import EXERCISE_NAME_MAX_LENGTH, ExerciseSettings, ItemKind

ExerciseName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=EXERCISE_NAME_MAX_LENGTH
    ),
]


class ExerciseRequest(BaseModel):
    """An exercise's editable fields. Updates replace all of them."""

    name: ExerciseName
    description: str | None = None
    collection_ids: list[int] = Field(
        min_length=1,
        description="Collections of the exercise's item kind to draw from.",
    )
    settings: ExerciseSettings


class NewExerciseRequest(ExerciseRequest):
    item_kind: ItemKind = Field(
        description="What it studies: words (`entries`) or `kanji`. Can't change."
    )


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    item_kind: ItemKind
    collection_ids: list[int] = Field(
        description="Empty if its collections were deleted; it can't run then."
    )
    settings: ExerciseSettings
    created_at: datetime
    updated_at: datetime
