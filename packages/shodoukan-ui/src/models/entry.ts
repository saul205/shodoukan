export interface Gloss {
  id: number
  text: string
  type: string | null
  lang: string
}

export interface CrossReference {
  reference: string
  reading: string | null
  sense_idx: number | null
}

export interface ExampleSentence {
  lang: string
  text: string
}

export interface Example {
  id: number
  source_name: string
  source_id: string | null
  text: string
  sentences: ExampleSentence[]
}

export interface Sense {
  id: number
  pos: string[]
  misc: string[]
  dialects: string[]
  info: string[]
  glosses: Gloss[]
  cross_references: CrossReference[]
  examples: Example[]
}

export interface Reading {
  id: number
  text: string
  no_kanji: boolean
  priority: string[]
  info: string[]
  restricted_to: string[]
}

export interface KanjiReading {
  id: number
  kanji: string
  priority: string[]
  info: string[]
}

export interface ScoreBreakdown {
  freq: number | null
  jlpt_bonus: number | null
  exact_match: boolean | null
  fts_rank: number | null
  sense_pos: number | null
  total_senses: number | null
  composite: number | null
}

export interface Entry {
  id: number
  kanji_readings: KanjiReading[]
  readings: Reading[]
  senses: Sense[]
  jlpt: number | null
  is_common: boolean
  score: ScoreBreakdown | null
}

export interface EntryKanjiLink {
  literal: string
}
