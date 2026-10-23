export interface KanjiMeaning {
  text: string
  lang: string
}

export interface Kanji {
  literal: string
  grade: number | null
  stroke_count: number
  freq: number | null
  jlpt: number | null
  on_readings: string[]
  kun_readings: string[]
  nanori: string[]
  meanings: KanjiMeaning[]
}

export interface Language {
  code: string
  label: string
}

export const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'en', label: 'English' },
  { code: 'es', label: 'Español' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
]

const _GLOSS_LANG: Record<string, string> = {
  en: 'eng', es: 'spa', fr: 'fre', de: 'ger',
}

export function glossLang(code: string): string {
  return _GLOSS_LANG[code] ?? code
}

/** One stroke of a KanjiVG drawing, in its 109 × 109 space (see KANJIVG_SIZE). */
export interface KanjiStroke {
  /** SVG path of the stroke's centre line; draw it unfilled with a round stroke. */
  path: string
  /** Where KanjiVG places the stroke's number, if it has one. */
  label: [number, number] | null
}

/** A character's strokes in Japanese writing order (KanjiVG). */
export interface KanjiStrokes {
  literal: string
  strokes: KanjiStroke[]
}
