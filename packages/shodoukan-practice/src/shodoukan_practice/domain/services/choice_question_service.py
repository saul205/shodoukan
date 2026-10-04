"""Build the questions of a choice-card session from the pool's study cards.

Each question picks an item and one of the exercise's directions, shows the
prompt fields, and offers one value of the answer field among distractors
taken from other items.

**A distractor is never a valid answer.** A question about item C shows C's
prompt values and asks for field A. A candidate text t is rejected if some
item X of the pool (C included) fits the prompt (shares a key with C in every
prompt field) and t matches one of X's A values. That covers shared readings,
homophones, synonyms and equal spellings. Fewer options are preferred to an
ambiguous one; an item no direction can ask about is skipped.

The randomness comes from the `rng` passed in, so tests can seed it.
"""

from collections.abc import Sequence
from random import Random

from ..entities import (
    ChoiceCardSettings,
    ChoiceOption,
    Direction,
    ExerciseQuestion,
    ShownField,
    StudyField,
)
from ..exceptions import ExercisePoolTooSmallError
from .study_field_service import FieldValue, StudyCard

MIN_POOL_SIZE = 2


def build_choice_questions(
    cards: Sequence[StudyCard], settings: ChoiceCardSettings, rng: Random
) -> list[ExerciseQuestion]:
    """The session's questions, in order, without ids.

    Raises `ExercisePoolTooSmallError` if fewer than two items can be asked
    about, or no question can be built.
    """
    eligible = [
        card for card in cards if any(_can_ask(card, d) for d in settings.directions)
    ]
    if len(eligible) < MIN_POOL_SIZE:
        raise ExercisePoolTooSmallError(
            f"the exercise needs at least {MIN_POOL_SIZE} items with the fields it "
            f"studies; its collections have {len(eligible)}"
        )
    order = list(eligible)
    rng.shuffle(order)
    wanted = settings.question_count or len(order)
    questions: list[ExerciseQuestion] = []
    for card in order:
        question = _question(card, cards, settings, rng, position=len(questions))
        if question is not None:
            questions.append(question)
        if len(questions) == wanted:
            break
    if not questions:
        raise ExercisePoolTooSmallError(
            "no question can be asked without an ambiguous option"
        )
    return questions


def _can_ask(card: StudyCard, direction: Direction) -> bool:
    return card.has(*direction.prompt, direction.answer)


def _question(
    card: StudyCard,
    pool: Sequence[StudyCard],
    settings: ChoiceCardSettings,
    rng: Random,
    position: int,
) -> ExerciseQuestion | None:
    """A question about `card`, trying its directions in random order."""
    directions = [d for d in settings.directions if _can_ask(card, d)]
    rng.shuffle(directions)
    for direction in directions:
        options = _options(card, pool, direction, settings.option_count, rng)
        if options is None:
            continue
        correct = options[0]
        rng.shuffle(options)
        shown = (*direction.prompt, direction.answer)
        back_fields = [*shown, *(f for f in settings.back_fields if f not in shown)]
        return ExerciseQuestion(
            id=None,
            position=position,
            item_id=card.item_id,
            prompt_fields=direction.prompt,
            answer_field=direction.answer,
            prompt=tuple(_shown(card, f, front=True) for f in direction.prompt),
            options=tuple(options),
            correct_option=options.index(correct),
            back=tuple(_shown(card, f) for f in back_fields if card.has(f)),
        )
    return None


def _options(
    card: StudyCard,
    pool: Sequence[StudyCard],
    direction: Direction,
    option_count: int,
    rng: Random,
) -> list[ChoiceOption] | None:
    """The right option first, then the distractors; None if there's none."""
    answer = rng.choice(card.answers(direction.answer))
    # Every key that answers this prompt, from any item that fits it.
    valid_keys = frozenset().union(
        *(
            other.keys(direction.answer)
            for other in pool
            if _fits_prompt(other, card, direction.prompt)
        )
    )
    taken = set(answer.keys)
    candidates = [other for other in pool if other.item_id != card.item_id]
    rng.shuffle(candidates)
    options = [ChoiceOption(text=answer.text, item_id=card.item_id)]
    for other in candidates:
        if len(options) == option_count:
            break
        value = _distractor(other, direction.answer, valid_keys | taken, rng)
        if value is not None:
            options.append(ChoiceOption(text=value.text, item_id=other.item_id))
            taken |= value.keys
    return options if len(options) > 1 else None


def _fits_prompt(
    other: StudyCard, card: StudyCard, prompt: Sequence[StudyField]
) -> bool:
    return all(other.keys(field) & card.keys(field) for field in prompt)


def _distractor(
    other: StudyCard, field: StudyField, excluded: frozenset[str], rng: Random
) -> FieldValue | None:
    """One of `other`'s values for `field` that shares no excluded key."""
    values = [v for v in other.answers(field) if not v.keys & excluded]
    return rng.choice(values) if values else None


def _shown(card: StudyCard, field: StudyField, *, front: bool = False) -> ShownField:
    """The front shows what can be asked (a word's usual form); the back,
    every value."""
    values = card.answers(field) if front else card.get(field)
    return ShownField(field=field, values=tuple(v.text for v in values))
