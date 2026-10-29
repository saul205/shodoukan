from factories import OTHER_USER_ID, USER_ID, make_entry

from shodoukan_practice.domain.entities import (
    Inflection,
    PracticeEntry,
    PracticeSentence,
    SentenceTranslation,
    SharedEntryCollection,
    SharedExample,
    SharedSentence,
    SharedSentenceWord,
)
from shodoukan_practice.domain.services import (
    merge_examples,
    preview_sentences,
    prune_examples,
    with_examples,
)

RICE = "ご飯を食べる。"
BREAD = "パンを食べる。"


def stored_entry(user_id: object = USER_ID, entry_id: int = 7) -> PracticeEntry:
    """食べる with ids: its senses are 70 (English) and 71 (Spanish)."""
    entry = make_entry(USER_ID if user_id is USER_ID else OTHER_USER_ID)
    entry.id = entry_id
    for i, sense in enumerate(entry.senses):
        sense.id = entry_id * 10 + i
        for j, gloss in enumerate(sense.glosses):
            gloss.id = entry_id * 100 + i * 10 + j
    return entry


def own_sentence(entry: PracticeEntry, text: str = BREAD) -> PracticeSentence:
    sentence = PracticeSentence.create_own(entry.user_id, text, "Eat bread.", "eng")
    sentence.id = 40
    sentence.add_word(
        3,
        6,
        entry_id=entry.id,
        sense_id=entry.senses[1].id,
        analysis=("食べる", "たべる", ["動詞"], Inflection(endings=(), form="終止形")),
    )
    sentence.words[0].id = 1
    return sentence


def dictionary_sentence(entry: PracticeEntry, text: str = RICE) -> PracticeSentence:
    sentence = PracticeSentence.from_dictionary(
        entry.user_id, text, [], word="食べる", entry_id=entry.id, sense_id=None
    )
    sentence.id = 41
    return sentence


def test_with_examples_puts_each_sentence_under_its_sense() -> None:
    entry = stored_entry()

    shared = with_examples(
        entry.to_shared(), entry, [own_sentence(entry), dictionary_sentence(entry)]
    )

    rice, bread = shared.senses[0].examples, shared.senses[1].examples
    assert [e.sentences[0].text for e in rice] == [RICE]  # no sense: the first
    [example] = bread
    assert example.origin == "added"
    assert example.version == (40, 0)
    assert [(s.lang, s.text) for s in example.sentences] == [
        ("jpn", BREAD),
        ("eng", "Eat bread."),
    ]
    assert example.word == SharedSentenceWord(
        start=3,
        end=6,
        lemma="食べる",
        reading="たべる",
        pos=["動詞"],
        endings=[],
        form="終止形",
    )


def test_a_copy_is_created_with_its_gap_and_analysis() -> None:
    owner = stored_entry()
    shared = with_examples(owner.to_shared(), owner, [own_sentence(owner)])
    mine = stored_entry(OTHER_USER_ID, entry_id=8)

    merge = merge_examples(mine, shared, [], created=True, source=5)

    [copy] = merge.created
    [word] = copy.words
    assert (copy.user_id, copy.origin, copy.text) == (OTHER_USER_ID, "added", BREAD)
    assert copy.translations == [SentenceTranslation(lang="eng", text="Eat bread.")]
    assert (copy.original_id, copy.source_id, copy.version) == (40, 40, (40, 0))
    assert copy.source_collection_ids == [5]
    assert (word.entry_id, word.sense_id) == (8, 81)
    assert (copy.surface(word), word.lemma, word.reading) == (
        "食べる",
        "食べる",
        "たべる",
    )


def test_a_version_the_user_has_is_linked_not_copied() -> None:
    owner = stored_entry()
    shared = with_examples(owner.to_shared(), owner, [own_sentence(owner)])
    mine = stored_entry(OTHER_USER_ID, entry_id=8)
    first = merge_examples(mine, shared, [], created=True, source=5).created[0]
    first.id = 90
    other_word = stored_entry(OTHER_USER_ID, entry_id=9)

    # The same sentence comes with another word, from another collection.
    merge = merge_examples(other_word, shared, [first], created=False, source=6)

    assert merge.created == []
    assert merge.changed == [first]
    assert [w.entry_id for w in first.words] == [8, 9]
    assert first.source_collection_ids == [5, 6]
    again = merge_examples(other_word, shared, [first], created=False, source=6)
    assert again.changed == []


def test_a_sentence_of_two_words_in_one_import_is_copied_once() -> None:
    owner = stored_entry()
    sentence = own_sentence(owner)
    shared = with_examples(owner.to_shared(), owner, [sentence])
    candidates: list[PracticeSentence] = []
    mine = stored_entry(OTHER_USER_ID, entry_id=8)

    first = merge_examples(mine, shared, candidates, created=True, source=None)
    # The second sense brings it again (a file listing it twice).
    second = merge_examples(mine, shared, candidates, created=True, source=None)

    assert len(first.created) == 1
    assert second.created == []
    assert len(candidates) == 1


def test_a_removed_copy_isnt_brought_back() -> None:
    owner = stored_entry()
    shared = with_examples(owner.to_shared(), owner, [own_sentence(owner)])
    mine = stored_entry(OTHER_USER_ID, entry_id=8)
    copy = merge_examples(mine, shared, [], created=True, source=5).created[0]
    copy.id = 90
    mine.dismiss_example(copy)

    assert merge_examples(mine, shared, [], created=False, source=5).created == []


def test_a_dictionary_sentence_is_located_and_takes_its_flag_when_created() -> None:
    owner = stored_entry()
    hidden = dictionary_sentence(owner)
    hidden.deactivate()
    shared = with_examples(owner.to_shared(), owner, [hidden])
    mine = stored_entry(OTHER_USER_ID, entry_id=8)
    theirs = dictionary_sentence(mine)

    merge = merge_examples(mine, shared, [theirs], created=True, source=None)

    assert merge.created == []
    assert merge.changed == [theirs]
    assert theirs.is_active is False
    # Not created by this import: the user's flag stays.
    theirs.activate()
    merge_examples(mine, shared, [theirs], created=False, source=None)
    assert theirs.is_active is True


def test_a_dictionary_sentence_the_user_lacks_isnt_made_up() -> None:
    owner = stored_entry()
    shared = with_examples(owner.to_shared(), owner, [dictionary_sentence(owner)])

    merge = merge_examples(
        stored_entry(OTHER_USER_ID, 8), shared, [], created=True, source=None
    )

    assert (merge.created, merge.changed) == ([], [])


def test_an_example_from_before_sentences_is_linked_without_a_gap() -> None:
    # A file exported before sentences: examples without `word`.
    owner = stored_entry()
    old = owner.to_shared()
    example = SharedExample(
        origin="added",
        id=3,
        sentences=[SharedSentence(lang="jpn", text=BREAD)],
    )
    shared = old.model_copy(
        update={
            "senses": [
                old.senses[0].model_copy(update={"examples": [example]}),
                old.senses[1],
            ]
        }
    )

    [copy] = merge_examples(
        stored_entry(OTHER_USER_ID, 8), shared, [], created=True, source=None
    ).created

    [word] = copy.words
    assert not word.has_span  # the analyzer finds it when stored
    assert (word.entry_id, word.sense_id) == (8, 80)


def test_prune_lets_go_of_untouched_copies_the_source_dropped() -> None:
    owner = stored_entry()
    shared = with_examples(owner.to_shared(), owner, [own_sentence(owner)])
    mine = stored_entry(OTHER_USER_ID, entry_id=8)
    kept = merge_examples(mine, shared, [], created=True, source=5).created[0]
    kept.id = 90
    dropped = PracticeSentence.copied(
        OTHER_USER_ID,
        "古い文。",
        [],
        is_active=True,
        original_id=30,
        source_id=30,
        edited_id=None,
        revision=0,
        source=5,
    )
    dropped.id = 91
    edited = dropped.model_copy(update={"id": 92, "edited_id": None})
    also_brought = dropped.model_copy(
        update={"id": 93, "source_collection_ids": [5, 6]}
    )
    new_version = SharedEntryCollection(name="verbs", items=[shared])

    changed, removed = prune_examples(
        [kept, dropped, edited, also_brought], new_version, 5
    )

    assert removed == [dropped]
    assert changed == [also_brought]
    assert also_brought.source_collection_ids == [6]
    assert kept.source_collection_ids == [5]


def test_preview_sentences() -> None:
    owner = stored_entry()
    shared = with_examples(
        owner.to_shared(), owner, [own_sentence(owner), dictionary_sentence(owner)]
    )

    rice, bread = preview_sentences(shared, OTHER_USER_ID)

    assert (rice.text, rice.origin, rice.id) == (RICE, "imported", None)
    assert (bread.text, bread.origin) == (BREAD, "added")
    [word] = bread.words
    assert (bread.surface(word), word.lemma, word.entry_id) == (
        "食べる",
        "食べる",
        None,
    )
