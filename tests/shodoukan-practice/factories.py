"""Domain entities used across the practice infrastructure tests."""

from datetime import UTC, datetime
from uuid import UUID

from shodoukan_practice.domain.clock import utc_now
from shodoukan_practice.domain.entities import (
    ChoiceCardSettings,
    ChoiceOption,
    Direction,
    EntryCollection,
    EntryExercise,
    ExerciseQuestion,
    ExerciseSession,
    KanjiCollection,
    KanjiExercise,
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
    ShownField,
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
) -> ExerciseQuestion:
    """Literal → kun'yomi for 食; option 0 is right."""
    return ExerciseQuestion(
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


def make_session(
    user_id: UUID,
    exercise_id: int | None = None,
    item_id: int | None = None,
    *,
    question_id: int | None = 1,
) -> ExerciseSession:
    """A kanji session started now (sessions go idle), with an active question
    (id `question_id`, None as if not stored yet) and no history."""
    now = utc_now()
    return ExerciseSession(
        id=None,
        user_id=user_id,
        exercise_id=exercise_id,
        exercise_name="N5 kanji",
        item_kind="kanji",
        meaning_lang="en",
        current=make_question(0, item_id, question_id),
        created_at=now,
        updated_at=now,
    )
