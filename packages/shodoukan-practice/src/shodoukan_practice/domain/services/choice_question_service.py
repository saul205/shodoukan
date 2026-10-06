"""Build the next question of a choice-card session from the pool's cards.

A question picks an item (see `question_order_service` for which one comes
next) and one of the exercise's directions, shows the prompt fields, and
offers one value of the answer field among distractors taken from other items.

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
    ChoiceQuestion,
    Direction,
    ExerciseQuestion,
    StudyField,
)
from ..exceptions import ExercisePoolTooSmallError
from .question_order_service import (
    back,
    can_ask,
    candidates,
    eligible_items,
    ensure_enough_items,
    fits_prompt,
    front,
)
from .study_field_service import FieldValue, StudyCard


def build_next_question(
    cards: Sequence[StudyCard],
    settings: ChoiceCardSettings,
    history: Sequence[ExerciseQuestion],
    rng: Random,
) -> ChoiceQuestion:
    """The next question, positioned after `history`, without an id.

    Raises `ExercisePoolTooSmallError` if the pool is too small or no item can
    be asked without an ambiguous option.
    """
    ensure_enough_items(cards, settings)
    eligible = eligible_items(cards, settings)
    for card in candidates(eligible, history, rng):
        question = _question(card, cards, settings, rng, position=len(history))
        if question is not None:
            return question
    raise ExercisePoolTooSmallError(
        "no question can be asked without an ambiguous option"
    )


def _question(
    card: StudyCard,
    pool: Sequence[StudyCard],
    settings: ChoiceCardSettings,
    rng: Random,
    position: int,
) -> ChoiceQuestion | None:
    """A question about `card`, trying its directions in random order."""
    directions = [d for d in settings.directions if can_ask(card, d)]
    rng.shuffle(directions)
    for direction in directions:
        options = _options(card, pool, direction, settings.option_count, rng)
        if options is None:
            continue
        correct = options[0]
        rng.shuffle(options)
        return ChoiceQuestion(
            id=None,
            position=position,
            item_id=card.item_id,
            prompt_fields=direction.prompt,
            answer_field=direction.answer,
            prompt=front(card, direction),
            options=tuple(options),
            correct_option=options.index(correct),
            back=back(card, direction, settings),
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
            if fits_prompt(other, card, direction.prompt)
        )
    )
    taken = set(answer.keys)
    others = [other for other in pool if other.item_id != card.item_id]
    rng.shuffle(others)
    options = [ChoiceOption(text=answer.text, item_id=card.item_id)]
    for other in others:
        if len(options) == option_count:
            break
        value = _distractor(other, direction.answer, valid_keys | taken, rng)
        if value is not None:
            options.append(ChoiceOption(text=value.text, item_id=other.item_id))
            taken |= value.keys
    return options if len(options) > 1 else None


def _distractor(
    other: StudyCard, field: StudyField, excluded: frozenset[str], rng: Random
) -> FieldValue | None:
    """One of `other`'s values for `field` that shares no excluded key."""
    values = [v for v in other.answers(field) if not v.keys & excluded]
    return rng.choice(values) if values else None
