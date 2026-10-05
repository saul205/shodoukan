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
  /** Only active (true) or inactive (false) items; all if undefined. */
  active?: boolean
}

export interface LibraryQuery extends SearchQuery {
  /** Leave out this collection's items (what can still be added to it). */
  not_in_collection?: number
}

/** A field an exercise can study; which ones apply depends on the item kind. */
export type StudyField = 'writing' | 'reading' | 'meaning' | 'literal' | 'onyomi' | 'kunyomi'

/** Show the `prompt` fields, ask for the `answer` field (never one of them). */
export interface Direction {
  prompt: StudyField[]
  answer: StudyField
}

/** A card with options: the right answer and wrong ones from the collections. */
export interface ChoiceCardSettings {
  type: 'card.choice'
  directions: Direction[]
  /** Shown on the back once answered, besides the prompt and the answer. */
  back_fields: StudyField[]
  option_count: number // 2–8
  distractor_source: 'collection'
}

/** Settings by exercise type, discriminated by `type`. */
export type ExerciseSettings = ChoiceCardSettings

export interface Exercise {
  id: number
  name: string
  description: string | null
  item_kind: ItemKind
  /** Empty if its collections were deleted; it can't run then. */
  collection_ids: number[]
  settings: ExerciseSettings
  created_at: string
  updated_at: string
}

/** An exercise's editable fields; an update replaces all of them. */
export interface ExerciseInput {
  name: string
  description: string | null
  collection_ids: number[]
  settings: ExerciseSettings
}

export interface NewExerciseInput extends ExerciseInput {
  /** Can't change once created. */
  item_kind: ItemKind
}

/** How a question is played; picks the player component. */
export type QuestionType = 'card.choice'

/** A field of the item as the card shows it, with all its values. */
export interface ShownField {
  field: StudyField
  values: string[]
}

export interface ChoiceOption {
  text: string
  /** The item the option comes from; null until the question is answered. */
  item_id: number | null
}

/** The option picked, by its index. */
export interface OptionAnswer {
  type: 'option'
  option: number
}

/** The question was skipped: it counts as a miss and its solution is shown. */
export interface SkipAnswer {
  type: 'skip'
}

/** Answers by type, discriminated by `type`. */
export type ExerciseAnswer = OptionAnswer | SkipAnswer

/**
 * A question of a session. Until it's answered the API hides its solution:
 * `item_id`, `correct_option`, `back` and the options' items are null.
 */
export interface ExerciseQuestion {
  type: QuestionType
  id: number
  position: number
  prompt_fields: StudyField[]
  answer_field: StudyField
  prompt: ShownField[]
  options: ChoiceOption[]
  answered: boolean
  item_id: number | null
  correct_option: number | null
  back: ShownField[] | null
  answer: ExerciseAnswer | null
  is_correct: boolean | null
  answered_at: string | null
  response_ms: number | null
}

export interface ExerciseSession {
  id: number
  /** Null if the exercise was deleted. */
  exercise_id: number | null
  exercise_name: string
  item_kind: ItemKind
  meaning_lang: string
  started_at: string
  last_activity_at: string
  /** When it was closed, or its last activity once idle; null while open. */
  finished_at: string | null
  answered: number
  score: number
  /** The active question, without its solution. */
  current: ExerciseQuestion | null
  /** The answered questions, in order, with their solutions. */
  history: ExerciseQuestion[]
}

export interface AnswerResult {
  /** The graded question, with its solution. */
  answered: ExerciseQuestion
  /** The new active question; null if no other can be made. */
  next: ExerciseQuestion | null
  answered_count: number
  score: number
  finished_at: string | null
}

export type SessionStatus = 'open' | 'finished'

/** A session in the history, without its questions. */
export interface SessionSummary {
  id: number
  exercise_id: number | null
  exercise_name: string
  item_kind: ItemKind
  started_at: string
  last_activity_at: string
  finished_at: string | null
  answered: number
  score: number
}

export interface SessionQuery extends PageQuery {
  exercise_id?: number
  /** Open (the one to resume) or finished, idle ones included. */
  status?: SessionStatus
}

/** Answer counts; `accuracy` is right over answered (0–1), null with no answers. */
export interface AnswerTotals {
  /** Sessions with at least one answer. */
  sessions: number
  answered: number
  correct: number
  accuracy: number | null
  mean_response_ms: number | null
}

export interface DirectionStatistics {
  /** The shown fields, in a fixed order. */
  prompt_fields: StudyField[]
  answer_field: StudyField
  answered: number
  correct: number
  accuracy: number | null
}

/** An item answered wrong, named as it is now in the library. */
export interface MissedItem {
  item_id: number
  /** A word's usual form, or the kanji. */
  label: string
  /** A word's reading, when `label` isn't it. */
  reading: string | null
  answered: number
  wrong: number
}

export interface ExerciseStatistics {
  exercise_id: number
  item_kind: ItemKind
  totals: AnswerTotals
  /** Most answered first. */
  directions: DirectionStatistics[]
  /** Most misses first. */
  most_missed: MissedItem[]
}

export interface DayActivity {
  /** YYYY-MM-DD, in the requested time zone. */
  day: string
  answered: number
  correct: number
}

export interface ExerciseSummary {
  exercise_id: number
  /** Its current name. */
  exercise_name: string
  item_kind: ItemKind
  sessions: number
  answered: number
  correct: number
  accuracy: number | null
  last_answered_at: string
}

export interface PracticeStatistics {
  totals: AnswerTotals
  /** Every day of the window, oldest first; today is the last. */
  activity: DayActivity[]
  /** Exercises with answers, most recently answered first. */
  exercises: ExerciseSummary[]
  most_missed_entries: MissedItem[]
  most_missed_kanji: MissedItem[]
}
