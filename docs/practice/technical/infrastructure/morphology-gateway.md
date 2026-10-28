# Morphology gateway

[← Technical documentation](../README.md)

`infrastructure/morphology/`: `SudachiMorphologyGateway` implements the domain's
[`MorphologyGateway`](../domain/repository-ports.md#morphologygateway) with
[SudachiPy](https://github.com/WorksApplications/sudachi.rs) and its `core`
dictionary. Sentences use it to propose their words, link them to the library and
know the form of a gap ([proposal](../../proposals/sentences.md)).

## `SudachiMorphologyGateway`

```python
SudachiMorphologyGateway(dictionary="core", split_mode="C")
```

- **Dictionary** (`sudachidict_core`, a dependency of the package): loaded once per
  gateway, in about 30 ms. A tokenizer is created per call, since tokenizers aren't
  safe to share between threads; analyzing a sentence takes about 0.1 ms.
- **Split mode C** (long units): it matches dictionary words best (日本語, not 日本 +
  語), so it links a gap to its word most often.
- Each Sudachi morpheme becomes a `Morpheme`: `surface()`, `dictionary_form()` as
  `lemma`, `reading_form()` (katakana) as `reading`, the first four fields of
  `part_of_speech()` as `pos` (without the `*` placeholders), the last two as
  `conjugation_type` and `conjugation_form` (`None` for `*`), and `begin()` /
  `end()` as character offsets.
- SudachiPy ships type stubs (`sudachipy.pyi`) without a `py.typed` marker:
  `mypy.ini` sets `follow_untyped_imports` for it, and the adapter imports from
  `sudachipy.sudachipy`, the module the stubs describe.

## Accuracy

Measured with [`sentence_analysis.py`](../testing.md#benchmarks) on 1000 random JMDict
example sentences of JLPT words (seed 0), the gap being the word's form in the
sentence (`examples.text`):

| | `core`, C | `core`, A | `small`, C |
|---|---|---|---|
| Gap on morpheme boundaries | 98 % | 99 % | 99 % |
| Gap linked to its word (`gap_dictionary_forms`) | 98 % | 97 % | 98 % |
| Reading right, words not inflected | 99 % | 99 % | 99 % |
| Distinct forms among inflected gaps | 44 | 44 | 44 |
| Size installed | 193 MB | 193 MB | 110 MB |

- A gap that isn't on morpheme boundaries is part of a longer unit (心地 in 使い心地,
  制度 in 新制度): its own text is analyzed instead.
- The words not linked are rare or literary forms (つまらぬ, 命ぜられた, 通ず) and
  compound verbs (降り出している, 差し上げた).
- The wrong readings are single kanji with several readings (空, 体, 中): the reason
  a gap's reading stays editable.
- `small` is as accurate on this sample, which is all JLPT vocabulary; `core` covers
  rarer words, which the user's own sentences may have, for 83 MB more in the image.

On a copy of pre's library (1891 examples, 569 of them the user's own), the conversion
and `analyze-sentences` found the gap of every sentence: 1322 from JMDict's form, 520
own ones written as is, 49 inflected or expressions (引いた, 持っていって, 首になった),
falling into 50 distinct forms.

## Tests

`infrastructure/test_sudachi_morphology_gateway.py`, with the real dictionary:
morphemes cover the sentence with the right offsets, an inflected verb (lemmas,
conjugation, reading, its inflection), a word that doesn't inflect, verbs of different
classes in the same form (飲んだ / 食べた, 読んで / 食べて, 呼ばれた / 食べられた), and a
kana word's lemma.
