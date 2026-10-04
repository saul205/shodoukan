"""Build the next question of a choice-card session from the pool's cards.

A question picks an item and one of the exercise's directions, shows the
prompt fields, and offers one value of the answer field among distractors
taken from other items.

**Which item comes next** is worked out from the session's history alone:

1. items answered wrong come back once `REVIEW_GAP` questions went by, but
   never twice in a row, so many misses can't keep the deck from moving on;
2. then the deck: every item once per round, in random order, before any
   repeats (a round ends when every item of the pool was asked in it);
3. then any other item, if the ones above can't make an unambiguous question.

The same item is never asked twice in a row.

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
# Questions to wait before an item answered wrong comes back.
REVIEW_GAP = 3


def eligible_items(
    cards: Sequence[StudyCard], settings: ChoiceCardSettings
) -> list[StudyCard]:
    """The items some direction of the exercise can ask about."""
    return [c for c in cards if any(_can_ask(c, d) for d in settings.directions)]


def ensure_enough_items(
    cards: Sequence[StudyCard], settings: ChoiceCardSettings
) -> None:
    """Raises `ExercisePoolTooSmallError` with fewer than `MIN_POOL_SIZE`."""
    eligible = len(eligible_items(cards, settings))
    if eligible < MIN_POOL_SIZE:
        raise ExercisePoolTooSmallError(
            f"the exercise needs at least {MIN_POOL_SIZE} items with the fields it "
            f"studies; its collections have {eligible}"
        )


def build_next_question(
    cards: Sequence[StudyCard],
    settings: ChoiceCardSettings,
    history: Sequence[ExerciseQuestion],
    rng: Random,
) -> ExerciseQuestion:
    """The next question, positioned after `history`, without an id.

    Raises `ExercisePoolTooSmallError` if the pool is too small or no item can
    be asked without an ambiguous option.
    """
    ensure_enough_items(cards, settings)
    eligible = eligible_items(cards, settings)
    for card in _candidates(eligible, history, rng):
        question = _question(card, cards, settings, rng, position=len(history))
        if question is not None:
            return question
    raise ExercisePoolTooSmallError(
        "no question can be asked without an ambiguous option"
    )


def _candidates(
    eligible: Sequence[StudyCard], history: Sequence[ExerciseQuestion], rng: Random
) -> list[StudyCard]:
    """The eligible items in the order to try them (see the module docs)."""
    by_id = {card.item_id: card for card in eligible}
    last = history[-1].item_id if history else None

    due = [by_id[i] for i in _due_for_review(history) if i in by_id and i != last]
    if history and _is_review(history, len(history) - 1):
        due = []  # the last one was a missed item coming back: deal from the deck
    asked = _asked_this_round(set(by_id), history)
    deck = [c for c in eligible if c.item_id not in asked and c.item_id != last]
    rest = [c for c in eligible if c.item_id not in asked and c.item_id == last]
    rest += [c for c in eligible if c.item_id in asked and c.item_id != last]
    rng.shuffle(deck)
    rng.shuffle(rest)
    ordered = [*due, *deck, *rest]
    return list({card.item_id: card for card in ordered}.values())


def _due_for_review(history: Sequence[ExerciseQuestion]) -> list[int]:
    """Items whose last answer was wrong, at least `REVIEW_GAP` questions ago,
    oldest first."""
    last_seen: dict[int, int] = {}
    for index, question in enumerate(history):
        if question.item_id is not None:
            last_seen[question.item_id] = index
    due = [
        (index, item_id)
        for item_id, index in last_seen.items()
        if history[index].is_correct is False and len(history) - index >= REVIEW_GAP
    ]
    return [item_id for _, item_id in sorted(due)]


def _is_review(history: Sequence[ExerciseQuestion], index: int) -> bool:
    """Whether question `index` asked again an item missed the last time."""
    item_id = history[index].item_id
    for earlier in reversed(history[:index]):
        if earlier.item_id == item_id:
            return earlier.is_correct is False
    return False


def _asked_this_round(pool: set[int], history: Sequence[ExerciseQuestion]) -> set[int]:
    """The pool items asked in the current round: a round ends as soon as
    every item of the pool was asked in it."""
    asked: set[int] = set()
    for question in history:
        if question.item_id in pool:
            asked.add(question.item_id)
            if asked == pool:
                asked = set()
    return asked


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
