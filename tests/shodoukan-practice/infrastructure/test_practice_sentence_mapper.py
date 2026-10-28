from factories import USER_ID

from shodoukan_practice.domain.entities import (
    Inflection,
    PracticeSentence,
    SentenceTranslation,
    SentenceWord,
)
from shodoukan_practice.infrastructure.db.mappers import (
    practice_sentence_to_db,
    practice_sentence_to_domain,
)


def make_sentence() -> PracticeSentence:
    return PracticeSentence(
        id=3,
        user_id=USER_ID,
        text="カーテンがゆっくり引かれた。",
        translations=[
            SentenceTranslation(lang="eng", text="The curtain was drawn."),
            SentenceTranslation(lang="spa", text="Se corrió la cortina."),
        ],
        words=[
            SentenceWord(
                id=1,
                start=9,
                end=13,
                lemma="引く",
                reading="ヒカレタ",
                pos=["動詞", "一般"],
                inflection=Inflection(endings=("れる", "た"), form="終止形"),
                entry_id=7,
                sense_id=70,
            ),
            SentenceWord(
                id=2,
                start=0,
                end=4,
                lemma="カーテン",
                reading="カーテン",
                inflection=Inflection(endings=(), form=None),
            ),
            SentenceWord(id=3, entry_id=8),
        ],
        notes="from the novel",
        origin="added",
        original_id=11,
        source_id=12,
        edited_id=13,
        revision=2,
        source_collection_ids=[4, "file"],
    )


def test_round_trip_keeps_the_entity() -> None:
    sentence = make_sentence()
    assert practice_sentence_to_domain(practice_sentence_to_db(sentence)) == sentence


def test_list_order_becomes_position() -> None:
    row = practice_sentence_to_db(make_sentence())
    assert [t.position for t in row.translations] == [0, 1]
    assert [w.position for w in row.words] == [0, 1, 2]


def test_an_analyzed_noun_keeps_empty_endings() -> None:
    row = practice_sentence_to_db(make_sentence())
    # NULL endings mean "not analyzed"; a noun alone has none.
    assert [w.inflection_endings for w in row.words] == [["れる", "た"], [], None]
