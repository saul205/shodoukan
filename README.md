# shodoukan

A Japanese-English dictionary platform built around the [JMDict](https://www.edrdg.org/jmdict/j_jmdict.html) and [KANJIDIC2](https://www.edrdg.org/wiki/index.php/KANJIDIC_Project) datasets.

## Components

### `shodoukan-db` (separate repo)

Rust pipeline that downloads JMDict and KANJIDIC2, processes them, and publishes a SQLite database as a GitHub Release asset on a monthly schedule.

The database is the shared artifact consumed by both components below.

### Python library *(planned)*

Package for building applications on top of the dictionary — lookups by reading, kanji, or meaning; kanji decomposition; and more.

### Web interface *(planned)*

Dictionary lookup UI in the style of [Jisho](https://jisho.org/). Search words by reading, kanji, or meaning; browse kanji with stroke count, JLPT level, and example words.

## Data sources

- **JMDict** (~400k entries): words, readings, senses, multilingual glosses, and example sentences.
- **KANJIDIC2** (~13k kanji): on/kun readings, meanings, school grade, frequency rank, and JLPT level.

Both datasets are maintained by [EDRDG](https://www.edrdg.org/) and distributed under [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
