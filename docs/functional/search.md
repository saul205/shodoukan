# Search — Functional Guide

## What you can search for

Shodoukan accepts any of the following as a search query:

| Input type | Example | Notes |
|---|---|---|
| Kanji | `食べる` | Direct match on written forms |
| Kana | `たべる` | Match on reading |
| Romaji | `taberu` | Automatically converted to hiragana |
| English gloss | `eat` | Full-text search across definitions |
| Other language gloss | `comer`, `manger` | Use the language selector to set the target language |

A single search always returns both **dictionary entries** (words) and **kanji** (individual characters) at the same time.

---

## Understanding results

### Dictionary entries

Each entry shows:
- **Primary form** — the most common written form (kanji reading), or the kana reading if no kanji form exists
- **Reading** — the kana pronunciation (shown above the primary form when a kanji form is present)
- **JLPT badge** — the level at which this word appears in the Japanese Language Proficiency Test (N5 = beginner, N1 = advanced)
- **Common badge** — marks words that appear frequently in newspapers and general use
- **Definitions** — grouped by sense, with part-of-speech tags (noun, verb, etc.) and the gloss text in the selected language

### Kanji sidebar

Related kanji characters appear alongside the entries. Each kanji card shows:
- The character at large size
- Meanings in the selected language
- Kun-readings (native Japanese) and On-readings (Chinese-derived)
- JLPT level badge

---

## Ranking

Results are ordered so the most useful words appear first:

1. **How well the word matches comes first.** An exact match of the written form or
   reading beats one that only starts with your search (searching `食` returns `食`
   before `食べる`). For meanings, the closest definitions (short ones like "water"
   rather than "suspension of water supply") come first.
2. **Within an equally good match, common, high-frequency words** rank above rare ones.
3. **JLPT words** receive a bonus — N5 words (most common) rank higher than unlisted words.
4. For meaning searches, a match in a word's **first meaning** counts most; later
   meanings count less and less. Having many meanings doesn't push a word down
   (水 isn't penalised for its other senses).

A romaji search such as `kami` looks up both the reading (かみ) and the meaning, and
shows them in one list ranked the same way. The number of results and the pages cover
every match: paging through shows each word once.

---

## Language support

The language selector controls which language is used for definitions. Supported languages:

| Code | Language |
|---|---|
| `en` | English |
| `es` | Spanish |
| `fr` | French |
| `de` | German |
| `ru` | Russian |
| `nl` | Dutch |
| `hu` | Hungarian |
| `sl` | Slovenian |

Kanji meanings are available in English, Spanish, French, and German only.
