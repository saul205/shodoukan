"""Pick the next question of a word handwriting session: write the word.

The same as for kanji (`handwriting_question_service`), a character per cell:
the answer is a word's first spelling (`writing`, okurigana included) or its
first reading (`reading`, in kana), by the direction. Only words whose every
character has a stroke order (KanjiVG, which draws the kana too) can be
written and graded, and none longer than `MAX_CELLS`; the caller passes which
characters have one (`drawable`).

**Any word that fits the prompt is right**, if it has as many characters: the
cells are shown, so a word of another length can't be what was meant. The
draft lists them (`accepted`), the asked one first; the caller fetches their
characters' strokes and turns it into the question.

The randomness comes from the `rng` passed in, so tests can seed it.
"""

from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from random import Random

from ..entities import (
    MAX_CELLS,
    Direction,
    ExerciseQuestion,
    HandwritingCardSettings,
    ReferenceKanji,
    ReferenceWord,
    ShownField,
    StudyField,
    WordHandwritingQuestion,
)
from ..exceptions import ExercisePoolTooSmallError
from .question_order_service import (
    can_ask,
    card_back,
    card_front,
    eligible_items,
    ensure_enough_items,
    fits_prompt,
    items_in_order,
)
from .study_field_service import StudyCard


@dataclass(frozen=True)
class WordHandwritingDraft:
    """A word handwriting question before its characters' strokes are fetched."""

    item_id: int
    direction: Direction
    prompt: tuple[ShownField, ...]
    back: tuple[ShownField, ...]
    # The words that are right, the asked one first, all as long.
    accepted: tuple[str, ...]

    @property
    def characters(self) -> frozenset[str]:
        """Every character whose strokes the question needs."""
        return frozenset(char for word in self.accepted for char in word)

    def question(
        self, position: int, references: Mapping[str, ReferenceKanji]
    ) -> WordHandwritingQuestion:
        """The question, graded against the accepted words' characters, as the
        dictionary draws them (`references`, by character). A word with a
        character without strokes is left out; the asked one must have them
        all, else `ExercisePoolTooSmallError` (the dictionary changed)."""
        words = [
            ReferenceWord(text=word, characters=tuple(references[c] for c in word))
            for word in self.accepted
            if all(c in references for c in word)
        ]
        if not words or words[0].text != self.accepted[0]:
            raise ExercisePoolTooSmallError(f"no stroke order for {self.accepted[0]}")
        return WordHandwritingQuestion(
            id=None,
            position=position,
            item_id=self.item_id,
            prompt_fields=self.direction.prompt,
            answer_field=self.direction.answer,
            prompt=self.prompt,
            back=self.back,
            words=tuple(words),
        )


def written_word(card: StudyCard, field: StudyField) -> str | None:
    """What the card asks to write for `field`: its first value."""
    values = card.answers(field)
    return values[0].text if values else None


def word_characters(
    cards: Sequence[StudyCard], settings: HandwritingCardSettings
) -> set[str]:
    """Every character the exercise's words could ask for, to ask the
    dictionary which ones it draws."""
    return {
        char
        for card in cards
        for direction in settings.directions
        if (word := written_word(card, direction.answer)) is not None
        for char in word
    }


def _writable(card: StudyCard, field: StudyField, drawable: Set[str]) -> str | None:
    word = written_word(card, field)
    if word is None or len(word) > MAX_CELLS or not set(word) <= drawable:
        return None
    return word


def _askable(
    card: StudyCard, settings: HandwritingCardSettings, drawable: Set[str]
) -> list[Direction]:
    return [
        d
        for d in settings.directions
        if can_ask(card, d) and _writable(card, d.answer, drawable) is not None
    ]


def writable_items(
    cards: Sequence[StudyCard], settings: HandwritingCardSettings, drawable: Set[str]
) -> list[StudyCard]:
    """The words some direction can ask to write."""
    return [c for c in cards if _askable(c, settings, drawable)]


def ensure_enough_writable_items(
    cards: Sequence[StudyCard], settings: HandwritingCardSettings, drawable: Set[str]
) -> None:
    """Raises `ExercisePoolTooSmallError` with fewer than `MIN_POOL_SIZE` words
    that can be written."""
    ensure_enough_items(writable_items(cards, settings, drawable), settings)


def draft_next_word_question(
    cards: Sequence[StudyCard],
    settings: HandwritingCardSettings,
    history: Sequence[ExerciseQuestion],
    drawable: Set[str],
    rng: Random,
) -> WordHandwritingDraft:
    """The next question, without the characters' strokes. Raises
    `ExercisePoolTooSmallError` if the pool is too small."""
    pool = writable_items(cards, settings, drawable)
    ensure_enough_items(pool, settings)
    for card in items_in_order(eligible_items(pool, settings), history, rng):
        directions = _askable(card, settings, drawable)
        if not directions:
            continue
        direction = rng.choice(directions)
        asked = _writable(card, direction.answer, drawable)
        assert asked is not None  # askable directions have a writable word
        others = [
            word
            for other in pool
            if other is not card
            and fits_prompt(other, card, direction.prompt)
            and (word := _writable(other, direction.answer, drawable)) is not None
            and word != asked
            and len(word) == len(asked)
        ]
        return WordHandwritingDraft(
            item_id=card.item_id,
            direction=direction,
            prompt=card_front(card, direction),
            back=card_back(card, direction, settings),
            accepted=tuple(dict.fromkeys([asked, *others])),
        )
    raise ExercisePoolTooSmallError("no word of the exercise can be asked")
