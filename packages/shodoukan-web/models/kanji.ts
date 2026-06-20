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
