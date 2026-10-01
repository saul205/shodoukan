# Dictionary Gateway

[← Technical documentation](../README.md)

How the practice app reads the shodoukan dictionary, and how dictionary data becomes
practice entities. Code: `src/shodoukan_practice/infrastructure/dictionary/`.

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

## Wiring

`api/deps.py`:

- `_get_dictionary()` builds one `Dictionary()` per process, cached with `lru_cache`.
  It's read-only, so it's safe to share. Its path comes from `SHODOUKAN_DB_PATH` (or
  the library's default), and the file is downloaded on first use if it's missing.
  See [configuration](../cross-cutting/configuration.md#dictionary-database).
- `get_dictionary_gateway()` returns a `ShodoukanDictionaryGateway` around it.

## Tests

- `infrastructure/test_shodoukan_mapper.py`: pure mapping, no database.
- `infrastructure/test_shodoukan_dictionary_gateway.py`: runs against a real
  dictionary SQLite built from the core library's test data (`tests/db_helpers.py`)
  through the `dictionary` fixture. See [testing](../testing.md).
