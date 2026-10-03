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

1. **Exact matches** come before prefix matches (searching `食` returns `食` before `食べる`)
2. **Common, high-frequency words** rank above rare ones
3. **JLPT words** receive a bonus — N5 words (most common) rank higher than unlisted words
4. For gloss searches, senses that appear **earlier in the entry** (primary meaning) rank higher than secondary meanings

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
