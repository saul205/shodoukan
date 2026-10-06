"""Which item a card session asks next, and what its card shows.

Shared by every card exercise type; each type's question service builds its
own question (options, references, ...) around the item picked here.

**Which item comes next** is worked out from the session's history alone:

1. items answered wrong (or drawn only close enough) come back once
   `REVIEW_GAP` questions went by, but never twice in a row, so many misses
   can't keep the deck from moving on;
2. then the deck: every item once per round, in random order, before any
   repeats (a round ends when every item of the pool was asked in it);
3. then any other item, if the ones above can't make a question.

The same item is never asked twice in a row.
"""

from collections.abc import Sequence
from random import Random

from ..entities import (
    CardSettings,
    Direction,
    ExerciseQuestion,
    ShownField,
    StudyField,
)
from ..exceptions import ExercisePoolTooSmallError
from .study_field_service import StudyCard

MIN_POOL_SIZE = 2
# Questions to wait before an item answered wrong comes back.
REVIEW_GAP = 3


def eligible_items(
    cards: Sequence[StudyCard], settings: CardSettings
) -> list[StudyCard]:
    """The items some direction of the exercise can ask about."""
    return [c for c in cards if any(can_ask(c, d) for d in settings.directions)]


def ensure_enough_items(cards: Sequence[StudyCard], settings: CardSettings) -> None:
    """Raises `ExercisePoolTooSmallError` with fewer than `MIN_POOL_SIZE`."""
    eligible = len(eligible_items(cards, settings))
    if eligible < MIN_POOL_SIZE:
        raise ExercisePoolTooSmallError(
            f"the exercise needs at least {MIN_POOL_SIZE} items with the fields it "
            f"studies; its collections have {eligible}"
        )


def items_in_order(
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


def can_ask(card: StudyCard, direction: Direction) -> bool:
    """Whether `card` has every field `direction` shows and asks."""
    return card.has(*direction.prompt, direction.answer)


def fits_prompt(
    other: StudyCard, card: StudyCard, prompt: Sequence[StudyField]
) -> bool:
    """Whether `other` answers `card`'s prompt too: it shares a key with it in
    every prompt field."""
    return all(other.keys(field) & card.keys(field) for field in prompt)


def card_front(card: StudyCard, direction: Direction) -> tuple[ShownField, ...]:
    """The front of the card: what can be asked of each prompt field (a word's
    usual form)."""
    return tuple(_shown(card, f, front=True) for f in direction.prompt)


def card_back(
    card: StudyCard, direction: Direction, settings: CardSettings
) -> tuple[ShownField, ...]:
    """The back of the card: the prompt, the answer and the exercise's back
    fields, each with every value."""
    shown = (*direction.prompt, direction.answer)
    fields = [*shown, *(f for f in settings.back_fields if f not in shown)]
    return tuple(_shown(card, f) for f in fields if card.has(f))


def _due_for_review(history: Sequence[ExerciseQuestion]) -> list[int]:
    """Items whose last answer needs a review (it was missed, or a drawing
    only close enough), at least `REVIEW_GAP` questions ago, oldest first."""
    last_seen: dict[int, int] = {}
    for index, question in enumerate(history):
        if question.item_id is not None:
            last_seen[question.item_id] = index
    due = [
        (index, item_id)
        for item_id, index in last_seen.items()
        if history[index].needs_review and len(history) - index >= REVIEW_GAP
    ]
    return [item_id for _, item_id in sorted(due)]


def _is_review(history: Sequence[ExerciseQuestion], index: int) -> bool:
    """Whether question `index` asked again an item due for review."""
    item_id = history[index].item_id
    for earlier in reversed(history[:index]):
        if earlier.item_id == item_id:
            return earlier.needs_review
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


def _shown(card: StudyCard, field: StudyField, *, front: bool = False) -> ShownField:
    """The front shows what can be asked (a word's usual form); the back,
    every value."""
    values = card.answers(field) if front else card.get(field)
    return ShownField(field=field, values=tuple(v.text for v in values))
