import pytest
from factories import USER_ID
from pydantic import ValidationError

from shodoukan_practice.domain.entities import (
    Inflection,
    PracticeSentence,
    SentenceTranslation,
    SentenceWord,
)
from shodoukan_practice.domain.exceptions import (
    EntityNotFoundError,
    OriginalDataError,
)

TEXT = "カーテンがゆっくり引かれた。"
PASSIVE_PAST = Inflection(endings=("れる", "た"), form="終止形")


def dictionary_sentence() -> PracticeSentence:
    return PracticeSentence.from_dictionary(
        USER_ID,
        TEXT,
        [
            SentenceTranslation(lang="jpn", text=TEXT),
            SentenceTranslation(lang="eng", text="The curtain was slowly drawn."),
        ],
        word="引かれた",
        entry_id=7,
        sense_id=70,
    )


def own_sentence(text: str = "毎朝、駅まで歩いて行きます。") -> PracticeSentence:
    sentence = PracticeSentence.create_own(
        USER_ID, text, "I walk to the station.", "eng"
    )
    sentence.words = [
        SentenceWord(id=1, start=3, end=4, entry_id=1),  # 駅
        SentenceWord(id=2, start=6, end=9, entry_id=2),  # 歩いて
    ]
    return sentence


def test_a_dictionary_sentence_marks_its_word() -> None:
    sentence = dictionary_sentence()

    [word] = sentence.words
    assert sentence.origin == "imported"
    assert sentence.translations == [
        SentenceTranslation(lang="eng", text="The curtain was slowly drawn.")
    ]
    assert sentence.surface(word) == "引かれた"
    assert (word.entry_id, word.sense_id) == (7, 70)
    assert not word.is_analyzed


def test_a_word_not_found_is_linked_without_a_span() -> None:
    sentence = PracticeSentence.from_dictionary(
        USER_ID, TEXT, [], word="引く", entry_id=7, sense_id=None
    )

    [word] = sentence.words
    assert not word.has_span
    assert word.entry_id == 7


def test_an_own_sentence_starts_without_words() -> None:
    sentence = PracticeSentence.create_own(USER_ID, "  駅まで歩く。 ", None, "eng")

    assert sentence.text == "駅まで歩く。"
    assert sentence.origin == "added"
    assert sentence.translations == []
    assert sentence.words == []


def test_a_sentence_cant_be_empty() -> None:
    with pytest.raises(ValueError):
        PracticeSentence.create_own(USER_ID, "  ", None, "eng")


def test_spans_must_be_inside_the_sentence_and_not_overlap() -> None:
    sentence = own_sentence()

    with pytest.raises(ValueError):
        sentence.add_word(8, 12)  # overlaps 歩いて
    with pytest.raises(ValueError):
        sentence.add_word(10, 40)  # past the end
    with pytest.raises(ValueError):
        sentence.mark_word(1, 5, 8)  # onto 歩いて
    with pytest.raises(ValidationError):
        SentenceWord(id=None, start=3, end=None)
    with pytest.raises(ValidationError):
        SentenceWord(id=None, start=4, end=4)
    assert [w.id for w in sentence.words] == [1, 2]


def test_add_and_remove_words() -> None:
    sentence = own_sentence()
    before = sentence.updated_at

    word = sentence.add_word(0, 2, entry_id=3)  # 毎朝
    sentence.add_word(None, None, entry_id=4)  # linked, no gap yet

    assert sentence.surface(word) == "毎朝"
    assert len(sentence.words) == 4
    assert sentence.updated_at > before
    sentence.remove_word(1)
    assert [w.id for w in sentence.words] == [2, None, None]
    with pytest.raises(EntityNotFoundError):
        sentence.remove_word(1)


def test_marking_a_word_again_drops_its_analysis() -> None:
    sentence = own_sentence()
    sentence.analyze_word(2, "歩く", "アルイテ", ["動詞", "一般"], PASSIVE_PAST)

    sentence.mark_word(2, 6, 8)

    word = sentence.words[1]
    assert sentence.surface(word) == "歩い"
    assert not word.is_analyzed
    assert word.inflection is None


def test_link_and_unlink() -> None:
    sentence = own_sentence()

    sentence.link_word(1, entry_id=9, sense_id=90)
    assert (sentence.words[0].entry_id, sentence.words[0].sense_id) == (9, 90)
    sentence.unlink_word(1)
    assert (sentence.words[0].entry_id, sentence.words[0].sense_id) == (None, None)
    assert sentence.words_of(2) == [sentence.words[1]]


def test_unchanged_calls_dont_touch() -> None:
    sentence = own_sentence()
    sentence.link_word(1, entry_id=1, sense_id=None)
    sentence.analyze_word(2, "歩く", "アルイテ", ["動詞"], None)
    before = sentence.updated_at

    sentence.link_word(1, entry_id=1, sense_id=None)
    sentence.analyze_word(2, "歩く", "アルイテ", ["動詞"], None)
    sentence.mark_word(2, 6, 9)
    sentence.activate()
    sentence.set_notes("  ")

    assert sentence.updated_at == before


def test_only_words_with_a_span_are_analyzed() -> None:
    sentence = own_sentence()
    sentence.add_word(None, None, entry_id=5)
    unmarked = sentence.words[-1]
    unmarked.id = 3

    with pytest.raises(ValueError):
        sentence.analyze_word(3, "x", "x", [], None)


def test_the_user_corrects_lemma_and_reading() -> None:
    sentence = PracticeSentence.create_own(USER_ID, "今日は休みです。", None, "eng")
    sentence.words = [SentenceWord(id=1, start=0, end=2, entry_id=1)]
    sentence.analyze_word(1, "今日", "キョウ", ["名詞"], None)

    sentence.correct_word(1, "今日", "こんにち")

    assert sentence.words[0].reading == "こんにち"
    with pytest.raises(ValueError):
        sentence.correct_word(1, "今日", "kyou")


def test_rewriting_an_own_sentence() -> None:
    sentence = own_sentence()
    sentence.translations.append(SentenceTranslation(lang="spa", text="Camino."))

    sentence.rewrite("毎晩、駅まで走って行きます。", "I run to the station.", "eng")

    assert sentence.text == "毎晩、駅まで走って行きます。"
    assert sentence.translations == [
        SentenceTranslation(lang="eng", text="I run to the station."),
        SentenceTranslation(lang="spa", text="Camino."),
    ]
    assert sentence.revision == 1
    station, walking = sentence.words
    assert sentence.surface(station) == "駅"  # still there, same place
    assert not walking.has_span  # 歩いて is gone: linked, no gap
    assert walking.entry_id == 2


def test_rewriting_to_a_shorter_sentence() -> None:
    sentence = own_sentence()

    sentence.rewrite("駅へ。", None, "eng")

    station, walking = sentence.words
    assert sentence.surface(station) == "駅"
    assert not walking.has_span


def test_rewriting_moves_a_word_that_moved() -> None:
    sentence = own_sentence()

    sentence.rewrite("駅まで、毎朝歩いて行きます。", None, "eng")

    station, walking = sentence.words
    assert sentence.surface(station) == "駅"
    assert sentence.surface(walking) == "歩いて"
    assert sentence.translations == []


def test_rewriting_to_the_same_text_changes_nothing() -> None:
    sentence = own_sentence()
    before = sentence.updated_at

    sentence.rewrite(sentence.text, "I walk to the station.", "eng")

    assert sentence.revision == 0
    assert sentence.updated_at == before


def test_dictionary_sentences_cant_be_rewritten() -> None:
    with pytest.raises(OriginalDataError):
        dictionary_sentence().rewrite("別の文。", None, "eng")


def test_no_japanese_translation() -> None:
    with pytest.raises(ValueError):
        PracticeSentence.create_own(USER_ID, "駅。", "駅。", "jpn")


def test_deactivate_and_notes() -> None:
    sentence = dictionary_sentence()

    sentence.deactivate()
    sentence.set_notes(" a note ")

    assert not sentence.is_active
    assert sentence.notes == "a note"
