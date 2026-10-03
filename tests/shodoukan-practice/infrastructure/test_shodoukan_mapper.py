from factories import USER_ID

from shodoukan.models.entry import (
    CrossReference,
    Entry,
    Example,
    ExampleSentence,
    Gloss,
    KanjiReading,
    Page,
    Reading,
    Sense,
)
from shodoukan.models.kanji import Kanji, KanjiMeaning
from shodoukan.models.search import SearchResult
from shodoukan_practice.infrastructure.dictionary import (
    shodoukan_entry_to_practice,
    shodoukan_kanji_to_practice,
    shodoukan_search_to_dictionary,
)


def make_dictionary_entry() -> Entry:
    return Entry(
        id=1000001,
        kanji_readings=[
            KanjiReading(id=7, kanji="食べる", priority=["ichi1"], info=[])
        ],
        readings=[
            Reading(
                id=8,
                text="たべる",
                no_kanji=False,
                priority=["ichi1"],
                info=[],
                restricted_to=[],
            )
        ],
        senses=[
            Sense(
                id=9,
                pos=["v1", "vt"],
                misc=[],
                dialects=[],
                info=[],
                glosses=[
                    Gloss(id=10, text="to eat", type=None, lang="eng"),
                    Gloss(id=11, text="comer", type=None, lang="spa"),
                ],
                cross_references=[
                    CrossReference(reference="食う", reading=None, sense_idx=None)
                ],
                examples=[
                    Example(
                        id=12,
                        source_name="tatoeba",
                        source_id="123",
                        text="食べる",
                        sentences=[
                            ExampleSentence(lang="jpn", text="ご飯を食べる。"),
                            ExampleSentence(lang="eng", text="I eat rice."),
                        ],
                    )
                ],
            )
        ],
        jlpt=5,
        is_common=True,
    )


def test_entry_becomes_a_fresh_snapshot_for_the_user() -> None:
    practice = shodoukan_entry_to_practice(make_dictionary_entry(), user_id=USER_ID)

    assert practice.id is None
    assert practice.user_id == USER_ID
    assert practice.source_entry_id == 1000001
    assert practice.jlpt == 5
    assert practice.is_common is True
    assert practice.is_active is True
    assert [kr.kanji for kr in practice.kanji_readings] == ["食べる"]
    assert [r.text for r in practice.readings] == ["たべる"]


def test_entry_keeps_every_language_and_marks_items_imported() -> None:
    sense = shodoukan_entry_to_practice(make_dictionary_entry(), USER_ID).senses[0]

    assert [(g.text, g.lang) for g in sense.glosses] == [
        ("to eat", "eng"),
        ("comer", "spa"),
    ]
    assert all(g.origin == "imported" and g.enabled for g in sense.glosses)
    assert [s.lang for s in sense.examples[0].sentences] == ["jpn", "eng"]


def test_dictionary_ids_are_not_copied_to_nested_items() -> None:
    practice = shodoukan_entry_to_practice(make_dictionary_entry(), USER_ID)
    sense = practice.senses[0]

    assert practice.readings[0].id is None
    assert sense.id is None
    assert sense.glosses[0].id is None
    assert sense.examples[0].id is None


def test_kanji_becomes_a_fresh_snapshot_for_the_user() -> None:
    kanji = Kanji(
        literal="食",
        grade=2,
        stroke_count=9,
        freq=316,
        jlpt=4,
        on_readings=["ショク", "ジキ"],
        kun_readings=["た.べる"],
        nanori=["あき"],
        meanings=[
            KanjiMeaning(text="eat", lang="en"),
            KanjiMeaning(text="comer", lang="es"),
        ],
    )

    practice = shodoukan_kanji_to_practice(kanji, user_id=USER_ID)

    assert practice.id is None
    assert practice.user_id == USER_ID
    assert practice.literal == "食"
    assert [r.text for r in practice.on_readings] == ["ショク", "ジキ"]
    assert [r.text for r in practice.kun_readings] == ["た.べる"]
    assert [r.text for r in practice.nanori] == ["あき"]
    assert [(m.text, m.lang, m.origin) for m in practice.meanings] == [
        ("eat", "en", "imported"),
        ("comer", "es", "imported"),
    ]


def test_search_result_becomes_read_models() -> None:
    result = SearchResult(
        entries=Page(items=[make_dictionary_entry()], total=7, limit=1, offset=2),
        kanji=[
            Kanji(
                literal="食",
                grade=2,
                stroke_count=9,
                freq=316,
                jlpt=4,
                on_readings=["ショク"],
                kun_readings=["た.べる"],
                nanori=[],
                meanings=[KanjiMeaning(text="eat", lang="en")],
            )
        ],
    )

    found = shodoukan_search_to_dictionary(result)

    assert (found.entries.total, found.entries.limit, found.entries.offset) == (7, 1, 2)
    entry = found.entries.items[0]
    assert entry.id == 1000001
    assert entry.is_common is True
    sense = entry.senses[0]
    assert [(g.text, g.lang) for g in sense.glosses] == [
        ("to eat", "eng"),
        ("comer", "spa"),
    ]
    assert sense.cross_references[0].reference == "食う"
    assert sense.cross_references[0].sense_index is None
    assert [s.text for s in sense.examples[0].sentences] == [
        "ご飯を食べる。",
        "I eat rice.",
    ]
    assert found.kanji[0].on_readings == ["ショク"]
    assert found.kanji[0].meanings[0].text == "eat"
