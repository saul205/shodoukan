// Response models of the practice API (shodoukan-practice). Dictionary
// results reuse the shodoukan-ui models (`Entry`, `Kanji`, `SearchResult`).

export type Origin = 'imported' | 'added'

export interface PracticeGloss {
  id: number
  text: string
  lang: string // ISO 639-2, e.g. "eng"
  type: string | null
  enabled: boolean
  origin: Origin
}

export interface PracticeExampleSentence {
  lang: string
  text: string
}

export interface PracticeExample {
  id: number
  text: string
  sentences: PracticeExampleSentence[]
  enabled: boolean
  origin: Origin
}

export interface PracticeSense {
  id: number
  pos: string[]
  misc: string[]
  dialects: string[]
  info: string[]
  glosses: PracticeGloss[]
  examples: PracticeExample[]
  notes: string | null
}

export interface PracticeReading {
  id: number
  text: string
  no_kanji: boolean
  info: string[]
  restricted_to: string[]
  enabled: boolean
}

export interface PracticeKanjiReading {
  id: number
  kanji: string
  info: string[]
  enabled: boolean
}

export interface PracticeEntry {
  id: number
  source_entry_id: number
  kanji_readings: PracticeKanjiReading[]
  readings: PracticeReading[]
  senses: PracticeSense[]
  jlpt: number | null
  is_common: boolean
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PracticeReadingItem {
  id: number
  text: string
  enabled: boolean
}

export interface PracticeKanjiMeaning {
  id: number
  text: string
  lang: string // ISO 639-1, e.g. "en"
  enabled: boolean
  origin: Origin
}

export interface PracticeKanji {
  id: number
  literal: string
  grade: number | null
  stroke_count: number
  freq: number | null
  jlpt: number | null
  on_readings: PracticeReadingItem[]
  kun_readings: PracticeReadingItem[]
  nanori: PracticeReadingItem[]
  meanings: PracticeKanjiMeaning[]
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export interface Collection {
  id: number
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

export interface CollectionInput {
  name: string
  description: string | null
}

/** Entries and kanji live in separate lists and collections, never mixed. */
export type ItemKind = 'entries' | 'kanji'

/** Parts of an entry that can be enabled or disabled, as in the API's URLs. */
export type EntryPart = 'kanji-readings' | 'readings' | 'glosses' | 'examples'
/** Parts of a kanji that can be enabled or disabled (readings = on, kun and nanori). */
export type KanjiPart = 'readings' | 'meanings'

export interface ImportStatus {
  entries: { source_entry_id: number; id: number }[]
  kanji: { literal: string; id: number }[]
}

export interface PracticeUser {
  id: string
  username: string
  created_at: string
}

export interface PageQuery {
  limit?: number
  offset?: number
}

/** Search of the library or a collection; best match first when `q` is set. */
export interface SearchQuery extends PageQuery {
  /** Spelling, reading (kanji, kana or romaji) or meaning; blank lists everything. */
  q?: string
  /** Language of the meanings to search, as stored: "eng" for entries, "en" for kanji. */
  meaning_lang?: string
}

export interface LibraryQuery extends SearchQuery {
  /** Only active (true) or inactive (false) items; all if undefined. */
  active?: boolean
  /** Leave out this collection's items (what can still be added to it). */
  not_in_collection?: number
}
