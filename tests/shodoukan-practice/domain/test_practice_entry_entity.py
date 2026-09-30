from datetime import UTC, datetime

from shodoukan_practice.domain.entities import (
    PracticeEntry,
    PracticeExample,
    PracticeExampleSentence,
    PracticeGloss,
    PracticeKanjiReading,
    PracticeReading,
    PracticeSense,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make_entry() -> PracticeEntry:
    return PracticeEntry(
        id=1,
        user_id=1,
        source_entry_id=1000001,
        kanji_readings=[
            PracticeKanjiReading(id=1, kanji="食べる", info=[]),
        ],
        readings=[
            PracticeReading(
                id=1,
                text="たべる",
                no_kanji=False,
                info=[],
                restricted_to=[],
            ),
        ],
        senses=[
            PracticeSense(
                id=1,
                pos=["v1"],
                misc=[],
                dialects=[],
                info=[],
                glosses=[
                    PracticeGloss(id=1, text="to eat", lang="eng", type=None),
                    PracticeGloss(
                        id=None,
                        text="jamar (coloquial)",
                        lang="spa",
                        type=None,
                        origin="added",
                    ),
                ],
                examples=[
                    PracticeExample(
                        id=1,
                        text="",
                        sentences=[
                            PracticeExampleSentence(lang="jpn", text="ご飯を食べる。"),
                        ],
                    ),
                ],
            ),
        ],
        jlpt=5,
        is_common=True,
        created_at=NOW,
        updated_at=NOW,
    )


def test_practice_entry_shape_and_defaults() -> None:
    entry = make_entry()
    assert entry.is_active is True
    assert entry.senses[0].glosses[0].enabled is True
    assert entry.senses[0].glosses[0].origin == "imported"
    assert entry.senses[0].glosses[1].origin == "added"


def test_practice_entry_serializes_round_trip() -> None:
    entry = make_entry()
    dumped = entry.model_dump()
    assert PracticeEntry.model_validate(dumped) == entry


def test_deactivate_and_activate_touch() -> None:
    item = make_entry()
    item.deactivate()
    assert item.is_active is False
    assert item.updated_at > NOW

    touched = item.updated_at
    item.activate()
    assert item.is_active is True
    assert item.updated_at >= touched


def test_activate_when_active_does_not_touch() -> None:
    item = make_entry()
    item.activate()

    assert item.updated_at == NOW
