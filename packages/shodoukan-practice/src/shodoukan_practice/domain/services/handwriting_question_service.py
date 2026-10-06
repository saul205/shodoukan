"""Pick the next question of a handwriting session: draw the kanji.

The item comes from `question_order_service`, like every card type. Only
kanji with a stroke order (KanjiVG) can be drawn and graded, so the others
aren't asked; the caller passes which literals have one (`drawable`), as the
dictionary says.

**Any kanji that fits the prompt is right.** Asked for the kanji read はし,
both 橋 and 箸 are right if both are in the pool, as a choice card would never
offer one as a wrong option for the other. The draft lists every kanji of the
pool that fits the prompt and can be drawn (`accepted`), the asked one first;
the caller fetches their strokes and turns the draft into the question, which
is graded against the closest of them.

The randomness comes from the `rng` passed in, so tests can seed it.
"""

from collections.abc import Sequence, Set
from dataclasses import dataclass
from random import Random

from ..entities import (
    Direction,
    ExerciseQuestion,
    HandwritingCardSettings,
    HandwritingQuestion,
    ReferenceKanji,
    ShownField,
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
from .study_field_service import StudyCard


@dataclass(frozen=True)
class HandwritingDraft:
    """A handwriting question before its kanji's strokes are fetched."""

    item_id: int
    direction: Direction
    prompt: tuple[ShownField, ...]
    back: tuple[ShownField, ...]
    # The kanji that are right, the asked one first.
    accepted: tuple[str, ...]

    def question(
        self, position: int, references: Sequence[ReferenceKanji]
    ) -> HandwritingQuestion:
        """The question, graded against `references` (the accepted kanji's
        strokes, as the dictionary has them)."""
        return HandwritingQuestion(
            id=None,
            position=position,
            item_id=self.item_id,
            prompt_fields=self.direction.prompt,
            answer_field=self.direction.answer,
            prompt=self.prompt,
            back=self.back,
            references=tuple(references),
        )


def literal(card: StudyCard) -> str | None:
    """The kanji of a kanji card."""
    values = card.answers("literal")
    return values[0].text if values else None


def drawable_items(cards: Sequence[StudyCard], drawable: Set[str]) -> list[StudyCard]:
    """The kanji that can be drawn: those with a stroke order."""
    return [c for c in cards if literal(c) in drawable]


def ensure_enough_drawable_items(
    cards: Sequence[StudyCard], settings: HandwritingCardSettings, drawable: Set[str]
) -> None:
    """Raises `ExercisePoolTooSmallError` with fewer than `MIN_POOL_SIZE`
    kanji that can be drawn."""
    ensure_enough_items(drawable_items(cards, drawable), settings)


def draft_next_question(
    cards: Sequence[StudyCard],
    settings: HandwritingCardSettings,
    history: Sequence[ExerciseQuestion],
    drawable: Set[str],
    rng: Random,
) -> HandwritingDraft:
    """The next question, without the kanji's strokes. Raises
    `ExercisePoolTooSmallError` if the pool is too small."""
    pool = drawable_items(cards, drawable)
    ensure_enough_items(pool, settings)
    for card in candidates(eligible_items(pool, settings), history, rng):
        directions = [d for d in settings.directions if can_ask(card, d)]
        if not directions:
            continue
        direction = rng.choice(directions)
        asked = literal(card)
        assert asked is not None  # drawable cards have a literal
        others = [
            text
            for other in pool
            if other is not card
            and fits_prompt(other, card, direction.prompt)
            and (text := literal(other)) is not None
            and text != asked
        ]
        return HandwritingDraft(
            item_id=card.item_id,
            direction=direction,
            prompt=front(card, direction),
            back=back(card, direction, settings),
            accepted=tuple(dict.fromkeys([asked, *others])),
        )
    raise ExercisePoolTooSmallError("no kanji of the exercise can be asked")
