"""Domain entities used across the practice infrastructure tests."""

from collections.abc import Sequence
from datetime import UTC, datetime
from random import Random
from uuid import UUID

from kanjivg_paths import PATHS

from shodoukan.utils.svg_path import path_points
from shodoukan_practice.domain.clock import utc_now
from shodoukan_practice.domain.entities import (
    ChoiceCardSettings,
    ChoiceOption,
    ChoiceQuestion,
    Direction,
    EntryCollection,
    EntryExercise,
    ExerciseSession,
    HandwritingCardSettings,
    HandwritingGrade,
    HandwritingQuestion,
    KanjiCollection,
    KanjiExercise,
    OptionAnswer,
    Point,
    PracticeEntry,
    PracticeExample,
    PracticeExampleSentence,
    PracticeGloss,
    PracticeKanji,
    PracticeKanjiMeaning,
    PracticeKanjiReading,
    PracticeReading,
    PracticeReadingItem,
    PracticeSense,
    ReferenceKanji,
    ReferenceStroke,
    ReferenceWord,
    ShownField,
    StrokeFeedback,
    Verdict,
    WordGrade,
    WordHandwritingQuestion,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)

# Practice users are keyed by the identity provider's user id (a UUID).
USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a001")
OTHER_USER_ID = UUID("8f14e45f-ceea-467a-9575-2ad4a6a1a002")

# For ORM rows built directly in tests: the database has no timestamp defaults.
TIMESTAMPS = {"created_at": NOW, "updated_at": NOW}


def make_entry(
    user_id: UUID, source_entry_id: int = 1000001, *, is_active: bool = True
) -> PracticeEntry:
    return PracticeEntry(
        id=None,
        user_id=user_id,
        source_entry_id=source_entry_id,
        kanji_readings=[PracticeKanjiReading(id=None, kanji="食べる", info=[])],
        readings=[
            PracticeReading(
                id=None, text="たべる", no_kanji=False, info=[], restricted_to=[]
            ),
            PracticeReading(
                id=None, text="くう", no_kanji=False, info=["ok"], restricted_to=[]
            ),
        ],
        senses=[
            PracticeSense(
                id=None,
                pos=["v1"],
                misc=[],
                dialects=[],
                info=[],
                glosses=[
                    PracticeGloss(id=None, text="to eat", lang="eng", type=None),
                    PracticeGloss(id=None, text="comer", lang="spa", type=None),
                ],
                examples=[
                    PracticeExample(
                        id=None,
                        text="",
                        sentences=[
                            PracticeExampleSentence(lang="jpn", text="ご飯を食べる。"),
                            PracticeExampleSentence(lang="eng", text="Eat rice."),
                        ],
                    ),
                ],
            ),
        ],
        jlpt=5,
        is_common=True,
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )


def make_kanji(
    user_id: UUID, literal: str = "食", *, is_active: bool = True
) -> PracticeKanji:
    return PracticeKanji(
        id=None,
        user_id=user_id,
        literal=literal,
        grade=2,
        stroke_count=9,
        freq=316,
        jlpt=4,
        on_readings=[PracticeReadingItem(id=None, text="ショク")],
        kun_readings=[
            PracticeReadingItem(id=None, text="た.べる"),
            PracticeReadingItem(id=None, text="く.う"),
        ],
        nanori=[],
        meanings=[
            PracticeKanjiMeaning(id=None, text="eat", lang="en"),
            PracticeKanjiMeaning(id=None, text="food", lang="en", origin="added"),
        ],
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )


def make_word(
    user_id: UUID,
    source_entry_id: int,
    spelling: str | None,
    reading: str,
    meanings: list[tuple[str, str]],
    *,
    created_at: datetime = NOW,
    is_active: bool = True,
) -> PracticeEntry:
    """An entry with one spelling (or none), one reading and one sense.

    `meanings` are `(text, lang)` pairs, e.g. `[("to eat", "eng")]`.
    """
    return PracticeEntry(
        id=None,
        user_id=user_id,
        source_entry_id=source_entry_id,
        kanji_readings=(
            [PracticeKanjiReading(id=None, kanji=spelling, info=[])] if spelling else []
        ),
        readings=[
            PracticeReading(
                id=None,
                text=reading,
                no_kanji=spelling is None,
                info=[],
                restricted_to=[],
            )
        ],
        senses=[
            PracticeSense(
                id=None,
                pos=["n"],
                misc=[],
                dialects=[],
                info=[],
                glosses=[
                    PracticeGloss(id=None, text=text, lang=lang, type=None)
                    for text, lang in meanings
                ],
                examples=[],
            )
        ],
        jlpt=None,
        is_common=False,
        is_active=is_active,
        created_at=created_at,
        updated_at=created_at,
    )


def make_kanji_with(
    user_id: UUID,
    literal: str,
    *,
    on: list[str] | None = None,
    kun: list[str] | None = None,
    meanings: list[tuple[str, str]] | None = None,
    created_at: datetime = NOW,
) -> PracticeKanji:
    """A kanji with the given readings and `(text, lang)` meanings."""
    return PracticeKanji(
        id=None,
        user_id=user_id,
        literal=literal,
        grade=None,
        stroke_count=1,
        freq=None,
        jlpt=None,
        on_readings=[PracticeReadingItem(id=None, text=text) for text in on or []],
        kun_readings=[PracticeReadingItem(id=None, text=text) for text in kun or []],
        nanori=[],
        meanings=[
            PracticeKanjiMeaning(id=None, text=text, lang=lang)
            for text, lang in meanings or []
        ],
        is_active=True,
        created_at=created_at,
        updated_at=created_at,
    )


def make_entry_collection(user_id: UUID, name: str = "verbs") -> EntryCollection:
    return EntryCollection(
        id=None, user_id=user_id, name=name, created_at=NOW, updated_at=NOW
    )


def make_kanji_collection(user_id: UUID, name: str = "N5") -> KanjiCollection:
    return KanjiCollection(
        id=None, user_id=user_id, name=name, created_at=NOW, updated_at=NOW
    )


def choice_settings(
    *directions: tuple[tuple[str, ...], str], **extra: object
) -> ChoiceCardSettings:
    """`ChoiceCardSettings` from `(prompt_fields, answer_field)` pairs."""
    return ChoiceCardSettings.model_validate(
        {
            "directions": [
                {"prompt": prompt, "answer": answer} for prompt, answer in directions
            ],
            **extra,
        }
    )


def handwriting_settings(
    *prompts: tuple[str, ...], **extra: object
) -> HandwritingCardSettings:
    """`HandwritingCardSettings` asking for the kanji from each of `prompts`."""
    return HandwritingCardSettings.model_validate(
        {
            "directions": [{"prompt": p, "answer": "literal"} for p in prompts],
            **extra,
        }
    )


def word_handwriting_settings(
    *directions: tuple[tuple[str, ...], str], **extra: object
) -> HandwritingCardSettings:
    """`HandwritingCardSettings` writing a word: (prompt fields, answer field)."""
    return HandwritingCardSettings.model_validate(
        {
            "directions": [{"prompt": p, "answer": a} for p, a in directions],
            **extra,
        }
    )


def make_entry_exercise(
    user_id: UUID, collection_ids: tuple[int, ...] = (), name: str = "Verbs"
) -> EntryExercise:
    """Meaning → writing and writing → meaning; reading on the back."""
    return EntryExercise(
        id=None,
        user_id=user_id,
        name=name,
        collection_ids=collection_ids,
        settings=ChoiceCardSettings(
            directions=(
                Direction(prompt=("meaning",), answer="writing"),
                Direction(prompt=("writing",), answer="meaning"),
            ),
            back_fields=("reading",),
        ),
        created_at=NOW,
        updated_at=NOW,
    )


def make_kanji_exercise(
    user_id: UUID, collection_ids: tuple[int, ...] = (), name: str = "N5 kanji"
) -> KanjiExercise:
    """Literal → kun'yomi, literal → on'yomi, kun'yomi → literal."""
    return KanjiExercise(
        id=None,
        user_id=user_id,
        name=name,
        collection_ids=collection_ids,
        settings=choice_settings(
            (("literal",), "kunyomi"),
            (("literal",), "onyomi"),
            (("kunyomi",), "literal"),
            back_fields=["meaning"],
        ),
        created_at=NOW,
        updated_at=NOW,
    )


def make_question(
    position: int, item_id: int | None = None, question_id: int | None = None
) -> ChoiceQuestion:
    """Literal → kun'yomi for 食; option 0 is right."""
    return ChoiceQuestion(
        id=question_id,
        position=position,
        item_id=item_id,
        prompt_fields=("literal",),
        answer_field="kunyomi",
        prompt=(ShownField(field="literal", values=("食",)),),
        options=(
            ChoiceOption(text="た.べる", item_id=item_id),
            ChoiceOption(text="みず", item_id=None),
            ChoiceOption(text="やま", item_id=None),
        ),
        correct_option=0,
        back=(
            ShownField(field="literal", values=("食",)),
            ShownField(field="kunyomi", values=("た.べる", "く.う")),
        ),
    )


# 一 as KanjiVG draws it: one stroke, left to right.
ICHI_PATH = "M11,54.25c3.19,0.62,6.25,0.75,9.73,0.5c20.64-1.5,50.39-5.12,68.58-5.24"


def make_reference(literal: str = "一") -> ReferenceKanji:
    """A reference kanji with one horizontal stroke."""
    return ReferenceKanji(
        literal=literal,
        strokes=(
            ReferenceStroke(
                path=ICHI_PATH,
                label=(4.25, 50.5),
                points=tuple((11.0 + 8 * i, 54.0) for i in range(11)),
            ),
        ),
    )


def make_handwriting_question(
    position: int,
    item_id: int | None = None,
    question_id: int | None = None,
    references: tuple[ReferenceKanji, ...] | None = None,
) -> HandwritingQuestion:
    """Meaning → literal for 一."""
    return HandwritingQuestion(
        id=question_id,
        position=position,
        item_id=item_id,
        prompt_fields=("meaning",),
        answer_field="literal",
        prompt=(ShownField(field="meaning", values=("one",)),),
        back=(
            ShownField(field="meaning", values=("one",)),
            ShownField(field="literal", values=("一",)),
        ),
        references=references or (make_reference(),),
    )


def make_reference_word(text: str = "一二") -> ReferenceWord:
    """A word whose characters are each one horizontal stroke."""
    return ReferenceWord(text=text, characters=tuple(make_reference(c) for c in text))


def make_word_question(
    position: int,
    item_id: int | None = None,
    question_id: int | None = None,
    words: tuple[str, ...] = ("一二",),
) -> WordHandwritingQuestion:
    """Meaning → writing for 一二 (a made-up word)."""
    return WordHandwritingQuestion(
        id=question_id,
        position=position,
        item_id=item_id,
        prompt_fields=("meaning",),
        answer_field="writing",
        prompt=(ShownField(field="meaning", values=("one two",)),),
        back=(
            ShownField(field="meaning", values=("one two",)),
            ShownField(field="writing", values=(words[0],)),
        ),
        words=tuple(make_reference_word(w) for w in words),
    )


def make_word_grade(verdict: Verdict = "correct", matched: str = "一二") -> WordGrade:
    cells = tuple(make_grade(verdict, c) for c in matched)
    return WordGrade(
        score=cells[0].score, verdict=verdict, matched=matched, cells=cells
    )


def make_grade(verdict: Verdict = "correct", matched: str = "一") -> HandwritingGrade:
    return HandwritingGrade(
        score={"correct": 95, "close": 70, "wrong": 20}[verdict],
        verdict=verdict,
        matched=matched,
        strokes=(StrokeFeedback(drawn=0, reference=0, status="ok"),),
    )


def make_session(
    user_id: UUID,
    exercise_id: int | None = None,
    item_id: int | None = None,
    *,
    question_id: int | None = 1,
    handwriting: bool = False,
    word: bool = False,
) -> ExerciseSession:
    """A kanji session started now (sessions go idle), with an active question
    (id `question_id`, None as if not stored yet) and no history. `word`
    makes it a words session writing 一二."""
    now = utc_now()
    current: ChoiceQuestion | HandwritingQuestion | WordHandwritingQuestion
    if word:
        current = make_word_question(0, item_id, question_id)
    elif handwriting:
        current = make_handwriting_question(0, item_id, question_id)
    else:
        current = make_question(0, item_id, question_id)
    return ExerciseSession(
        id=None,
        user_id=user_id,
        exercise_id=exercise_id,
        exercise_name="Words" if word else "N5 kanji",
        item_kind="entries" if word else "kanji",
        meaning_lang="eng" if word else "en",
        current=current,
        created_at=now,
        updated_at=now,
    )


# (item id, right?, answered at, prompt fields, answer field)
Answer = tuple[int | None, bool, datetime, tuple[str, ...], str]


def answered(
    item_id: int | None,
    correct: bool,
    at: datetime,
    prompt: tuple[str, ...] = ("literal",),
    answer: str = "kunyomi",
) -> Answer:
    return (item_id, correct, at, prompt, answer)


def make_answered_session(
    user_id: UUID,
    exercise_id: int | None,
    answers: list[Answer],
    *,
    item_kind: str = "kanji",
    started_at: datetime | None = None,
    last_activity_at: datetime | None = None,
    finished_at: datetime | None = None,
    response_ms: int | None = 1000,
) -> ExerciseSession:
    """A session whose history is `answers` (no active question). It starts at
    the first answer and was last active at the last one unless told."""
    history = []
    for position, (item_id, correct, at, prompt, answer_field) in enumerate(answers):
        question = make_question(position, item_id).model_copy(
            update={
                "prompt_fields": prompt,
                "answer_field": answer_field,
                "answer": OptionAnswer(option=0 if correct else 1),
                "is_correct": correct,
                "answered_at": at,
                "response_ms": response_ms,
            }
        )
        history.append(question)
    first = answers[0][2] if answers else utc_now()
    last = answers[-1][2] if answers else first
    return ExerciseSession.model_validate(
        {
            "id": None,
            "user_id": user_id,
            "exercise_id": exercise_id,
            "exercise_name": "N5 kanji",
            "item_kind": item_kind,
            "meaning_lang": "en",
            "history": history,
            "finished_at": finished_at,
            "created_at": started_at or first,
            "updated_at": last_activity_at or last,
        }
    )


def kanjivg_reference(literal: str) -> ReferenceKanji:
    """A character as KanjiVG draws it (`kanjivg_paths.PATHS`), with its
    centre lines as points, as the dictionary gateway gives them."""

    return ReferenceKanji(
        literal=literal,
        strokes=tuple(
            ReferenceStroke(path=d, label=None, points=tuple(path_points(d, 2)))
            for d in PATHS[literal]
        ),
    )


def hand_drawn(
    strokes: Sequence[Sequence[Point]], seed: int = 1, scale: float = 0.9
) -> tuple[tuple[Point, ...], ...]:
    """`strokes` as drawn by hand: resized by `scale` around the centre, each
    stroke a little out of place, every point shaky."""
    rng = Random(seed)
    shaken = []
    for stroke in strokes:
        ox, oy = rng.uniform(-2, 2), rng.uniform(-2, 2)
        shaken.append(
            tuple(
                (
                    (x - 54.5) * scale + 54.5 + ox + rng.gauss(0, 1),
                    (y - 54.5) * scale + 54.5 + oy + rng.gauss(0, 1),
                )
                for x, y in stroke[::2]
            )
        )
    return tuple(shaken)


def kanjivg_strokes(literal: str) -> list[tuple[Point, ...]]:
    return [s.points for s in kanjivg_reference(literal).strokes]
