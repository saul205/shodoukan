# Dictionary Gateway

[← Technical documentation](../README.md)

How the practice app reads the shodoukan dictionary, both to import items and to
search, and how dictionary data becomes practice models. Code: `src/shodoukan_practice/infrastructure/dictionary/`.

## Integration model

The practice app uses the `shodoukan` library **in-process**, the same way
`shodoukan-api` does. It opens the dictionary SQLite read-only through
`shodoukan.Dictionary`, with no HTTP hop. Each app wires its own instance. Why:
[decisions](../decisions.md#the-dictionary-is-used-in-process-behind-a-port).

```
use case ──► DictionaryGateway (domain port)
                    ▲
                    │ implements
        ShodoukanDictionaryGateway ──► shodoukan.Dictionary ──► dictionary SQLite
                    │
                    └─► shodoukan_mapper (anti-corruption layer)
```

The domain only knows the [`DictionaryGateway`](../domain/repository-ports.md#dictionarygateway)
port. Replacing the in-process adapter with an HTTP client for `shodoukan-api` would
mean writing a new adapter; use cases wouldn't change.

## `ShodoukanDictionaryGateway`

| Method | Uses | Returns |
|---|---|---|
| `new_practice_entry(source_entry_id, user_id)` | `Dictionary.get_entry(id)` | a fresh `PracticeEntry`, or `None` |
| `new_practice_kanji(literal, user_id)` | `Dictionary.get_kanji(literal)` | a fresh `PracticeKanji`, or `None` |
| `search(query, lang, limit, offset)` | `Dictionary.search(...)` | `DictionarySearchResult` read models |
| `get_entry(entry_id)` | `Dictionary.get_entry(id)` | a `DictionaryEntry`, or `None` |
| `get_kanji(literal)` | `Dictionary.get_kanji(literal)` | a `DictionaryKanji`, or `None` |
| `entries_for_kanji(literal, limit, offset)` | `Dictionary.get_entries_for_kanji(...)` | a `DictionaryEntryPage` of the words written with the kanji |
| `kanji_for_entry(entry_id)` | `Dictionary.get_kanji_for_entry_related(id)` | the `DictionaryKanji` in the entry's spellings (empty for kana-only words) |
| `kanji_strokes(literal)` | `Dictionary.get_kanji_strokes(literal)` | `DictionaryKanjiStrokes` (KanjiVG stroke order), or `None` |
| `literals_with_strokes(literals)` | `Dictionary.literals_with_strokes(literals)` | which of them have a stroke order (one query, no drawing read) |
| `stroke_references(literals)` | `Dictionary.get_kanji_strokes(literal)` per literal | `ReferenceKanji` by literal, for those with a stroke order: each stroke's path, number place and centre line as points (`path_points`, every `REFERENCE_POINT_SPACING` = 2 units), to grade drawings against |

"Fresh" means not stored yet: all ids are `None`, every part is enabled, and
glosses, examples and meanings have `origin="imported"`. Both dictionary calls return
**every language**, so the snapshot keeps them all.

## Anti-corruption mapping (`shodoukan_mapper.py`)

`shodoukan_entry_to_practice(entry, user_id)` and
`shodoukan_kanji_to_practice(kanji, user_id)` translate the dictionary's models into
practice entities. The domain never imports `shodoukan`.

| Dictionary | Practice | Notes |
|---|---|---|
| `Entry.id` | `PracticeEntry.source_entry_id` | the only link back to the dictionary |
| `Kanji.literal` | `PracticeKanji.literal` | the only link back |
| nested ids (readings, senses, glosses, examples) | `None` | the snapshot gets its own ids when stored |
| `Kanji.on_readings` / `kun_readings` / `nanori` (strings) | `PracticeReadingItem`s | each gets its own identity |
| `priority`, `cross_references`, `score`, example `source_name` / `source_id` | dropped | not needed for practice |

## Search

`search` delegates to `Dictionary.search`, the same function `shodoukan-api`'s
`/search` uses, so results, ranking and query detection are identical. Nothing is
reimplemented: improvements to search belong in the `shodoukan` library and reach both
apps. `shodoukan_search_to_dictionary(result)` maps the results to the read models,
which keep the entry `id` and kanji `literal` (what the import endpoints take), every
language, cross-references (`sense_idx` becomes `sense_index`) and examples. Priority
tags, nested row ids, example provenance and debug scores are dropped.

## Details

The entry and kanji detail pages read single items through `get_entry`, `get_kanji`,
`entries_for_kanji` and `kanji_for_entry`. They map with the same functions as the
search (`shodoukan_entry_to_dictionary`, `shodoukan_kanji_to_dictionary`,
`shodoukan_entry_page_to_dictionary`), so a result looks the same wherever it's shown.
These mirror `shodoukan-api`'s `/entries/{id}`, `/entries/{id}/kanji`, `/kanji/{literal}`
and `/entries/by-kanji/{literal}`, except that an entry's kanji come back whole instead
of as bare literals, so the page needs one request instead of one per kanji.

`kanji_strokes` reads the stroke order the library parses from KanjiVG (the dictionary
database's `kanji_svg` table) and maps it with `shodoukan_kanji_strokes_to_dictionary`.
The parsing and the fallback for compatibility ideographs live in the library only, so
both apps draw the same strokes. Why KanjiVG and not hanzi-writer:
[decisions](../decisions.md#stroke-order-comes-from-kanjivg-without-a-hanzi-writer-fallback).

## `ShodoukanKanaGateway`

Implements `KanaGateway` with the `shodoukan` library's text tools: `is_romaji` /
`to_hiragana` (Hepburn romaji, as in dictionary search) and `hiragana_to_katakana` /
`katakana_to_hiragana`. The query is trimmed; kana-only text (including the long-vowel
mark ー) keeps its spelling in both scripts. Anything else returns `None`. It lives here
because it's the same in-process use of `shodoukan` behind a port as the dictionary
([decisions](../decisions.md#romaji-goes-through-a-kanagateway-port)).

## Wiring

`api/deps.py`:

- `_get_dictionary()` builds one `Dictionary()` per process, cached with `lru_cache`.
  It's read-only, so it's safe to share. Its path comes from `SHODOUKAN_DB_PATH` (or
  the library's default), and the file is downloaded on first use if it's missing.
  See [configuration](../cross-cutting/configuration.md#dictionary-database).
- `get_dictionary_gateway()` returns a `ShodoukanDictionaryGateway` around it. It
  serves both the import use cases and `SearchDictionary`.

## Tests

- `infrastructure/test_shodoukan_mapper.py`: pure mapping, no database.
- `infrastructure/test_shodoukan_kana_gateway.py`: romaji and kana in both scripts,
  and text that isn't either.
- `infrastructure/test_shodoukan_dictionary_gateway.py`: runs against a real
  dictionary SQLite built from the core library's test data (`tests/db_helpers.py`)
  through the `dictionary` fixture. See [testing](../testing.md).
