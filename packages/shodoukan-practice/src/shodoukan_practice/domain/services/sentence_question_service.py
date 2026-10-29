"""Build the next question of a sentence-choice session.

The item asked is still a word of the pool (`question_order_service` picks
which, so reviews and rounds work as for cards); the question shows it in one
of its sentences (`GapText`, its gap there), the least used so far, and asks one of the
exercise's directions:

- **writing** (fill the gap): the gap is hidden. The options are the gap's
  text and those of other words' gaps in the same form: the same part of
  speech and inflection (引かれた among 飲まれた, 押された), so an ending never
  gives the answer away. No conjugation is made up: with too few gaps in
  that form, fewer options; with none, the direction isn't asked.
- **reading**: the word is shown in the sentence; the options are its reading
  in context and those of other gaps in the same form.
- **meaning**: the options are meanings, with the card rule
  (`choice_options`).

A distractor is never a valid answer: never the same text, and never from a
word that fits the prompt (it would fit the gap too). The randomness comes
from `rng`.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from random import Random

from ..entities import (
    ChoiceOption,
    Direction,
    ExerciseQuestion,
    SentenceChoiceQuestion,
    SentenceChoiceSettings,
)
from ..exceptions import ExercisePoolTooSmallError
from ..repositories import GapText
from .choice_question_service import choice_options
from .question_order_service import (
    MIN_POOL_SIZE,
    can_ask,
    card_back,
    card_front,
    fits_prompt,
    items_in_order,
)
from .study_field_service import StudyCard, kana_key


def askable_items(
    cards: Sequence[StudyCard], gaps: Mapping[int, Sequence[GapText]]
) -> list[StudyCard]:
    """The words that have a sentence to be asked in."""
    return [card for card in cards if gaps.get(card.item_id)]


def ensure_enough_sentence_items(
    cards: Sequence[StudyCard], gaps: Mapping[int, Sequence[GapText]]
) -> None:
    """Raises `ExercisePoolTooSmallError` with fewer than `MIN_POOL_SIZE` words
    that have a sentence."""
    if len(askable_items(cards, gaps)) < MIN_POOL_SIZE:
        raise ExercisePoolTooSmallError(
            f"a sentence exercise needs at least {MIN_POOL_SIZE} words with a sentence"
        )


def build_next_sentence_question(
    cards: Sequence[StudyCard],
    gaps: Mapping[int, Sequence[GapText]],
    settings: SentenceChoiceSettings,
    history: Sequence[ExerciseQuestion],
    rng: Random,
) -> SentenceChoiceQuestion:
    """The next question, positioned after `history`, without an id.

    `gaps` are each word's sentences it can be asked in, by item id. Raises
    `ExercisePoolTooSmallError` if too few words have a sentence, or none can
    be asked without an ambiguous option.
    """
    ensure_enough_sentence_items(cards, gaps)
    askable = askable_items(cards, gaps)
    used = Counter(
        q.sentence_id
        for q in history
        if isinstance(q, SentenceChoiceQuestion) and q.sentence_id is not None
    )
    for card in items_in_order(askable, history, rng):
        question = _question(card, cards, gaps, settings, used, rng, len(history))
        if question is not None:
            return question
    raise ExercisePoolTooSmallError(
        "no question can be asked without an ambiguous option"
    )


def _question(
    card: StudyCard,
    pool: Sequence[StudyCard],
    gaps: Mapping[int, Sequence[GapText]],
    settings: SentenceChoiceSettings,
    used: Counter[int],
    rng: Random,
    position: int,
) -> SentenceChoiceQuestion | None:
    gap = _least_used(gaps[card.item_id], used, rng)
    directions = [d for d in settings.directions if can_ask(card, d)]
    rng.shuffle(directions)
    for direction in directions:
        options = _options(card, gap, pool, gaps, direction, settings, rng)
        if options is None:
            continue
        correct = options[0]
        rng.shuffle(options)
        return SentenceChoiceQuestion(
            id=None,
            position=position,
            item_id=card.item_id,
            prompt_fields=direction.prompt,
            answer_field=direction.answer,
            prompt=card_front(card, direction),
            options=tuple(options),
            correct_option=options.index(correct),
            back=card_back(card, direction, settings),
            sentence_id=gap.sentence_id,
            sentence=gap.sentence,
            gap_start=gap.start,
            gap_end=gap.end,
            translation=gap.translation if settings.show_translation else None,
        )
    return None


def _least_used(gaps: Sequence[GapText], used: Counter[int], rng: Random) -> GapText:
    """One of the word's sentences used the fewest times so far."""
    fewest = min(used[g.sentence_id] for g in gaps)
    return rng.choice([g for g in gaps if used[g.sentence_id] == fewest])


def _options(
    card: StudyCard,
    gap: GapText,
    pool: Sequence[StudyCard],
    gaps: Mapping[int, Sequence[GapText]],
    direction: Direction,
    settings: SentenceChoiceSettings,
    rng: Random,
) -> list[ChoiceOption] | None:
    """The right option first, then the distractors; None if there's none."""
    if direction.answer == "meaning":
        return choice_options(card, pool, direction, settings.option_count, rng)
    reading = direction.answer == "reading"

    def key(text: str) -> str:
        return kana_key(text) if reading else text

    def value(g: GapText) -> str:
        return g.reading if reading else g.surface

    answer = value(gap)
    taken = {key(answer)}
    # Words that fit the prompt would fit the gap too: never their options.
    fitting = {o.item_id for o in pool if fits_prompt(o, card, direction.prompt)}
    others = [o for o in pool if o.item_id not in fitting]
    rng.shuffle(others)
    options = [ChoiceOption(text=answer, item_id=card.item_id)]
    for other in others:
        if len(options) == settings.option_count:
            break
        alike = [
            g
            for g in gaps.get(other.item_id, ())
            if g.form == gap.form and key(value(g)) not in taken
        ]
        if alike:
            chosen = rng.choice(alike)
            options.append(ChoiceOption(text=value(chosen), item_id=other.item_id))
            taken.add(key(value(chosen)))
    return options if len(options) > 1 else None
