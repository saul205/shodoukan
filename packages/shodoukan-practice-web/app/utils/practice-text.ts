import type { PracticeEntry, PracticeKanji } from '~/models/practice'

// How library items are named on cards and titles.

/** The entry's main written form: its first enabled spelling, else its first reading. */
export function entryHeadword(entry: PracticeEntry): string {
  const spelling = entry.kanji_readings.find(k => k.enabled) ?? entry.kanji_readings[0]
  return spelling?.kanji ?? entry.readings[0]?.text ?? ''
}

/** The reading shown above the headword (none when the headword is already kana). */
export function entryReading(entry: PracticeEntry): string {
  if (!entry.kanji_readings.length) return ''
  return (entry.readings.find(r => r.enabled) ?? entry.readings[0])?.text ?? ''
}

/** Enabled meanings of the entry in one language (ISO 639-2), first sense first. */
export function entryMeanings(entry: PracticeEntry, glossLang: string): string[] {
  return entry.senses.flatMap(s => s.glosses.filter(g => g.enabled && g.lang === glossLang).map(g => g.text))
}

/** Enabled meanings of the kanji in one language (ISO 639-1). */
export function kanjiMeanings(kanji: PracticeKanji, lang: string): string[] {
  return kanji.meanings.filter(m => m.enabled && m.lang === lang).map(m => m.text)
}
