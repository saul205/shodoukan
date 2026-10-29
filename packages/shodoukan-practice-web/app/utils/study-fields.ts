import type { ChoiceCardSettings, Direction, ExerciseType, HandwritingCardSettings, ItemKind, SentenceChoiceSettings, StudyField } from '~/models/practice'

// The fields an exercise can study, per item kind, and how they're named in
// the UI. Mirrors ENTRY_FIELDS / KANJI_FIELDS in the practice backend.

export const STUDY_FIELDS: Record<ItemKind, StudyField[]> = {
  entries: ['writing', 'reading', 'meaning'],
  kanji: ['literal', 'onyomi', 'kunyomi', 'meaning'],
}

export const FIELD_LABELS: Record<StudyField, string> = {
  writing: 'Escritura',
  reading: 'Lectura',
  meaning: 'Significado',
  literal: 'Kanji',
  onyomi: "On'yomi",
  kunyomi: "Kun'yomi",
}

export const ITEM_KIND_LABELS: Record<ItemKind, string> = {
  entries: 'Palabras',
  kanji: 'Kanji',
}

export const EXERCISE_TYPE_LABELS: Record<ExerciseType, string> = {
  'card.choice': 'Elegir entre opciones',
  'card.handwriting': 'Escribir a mano',
  'sentence.choice': 'En frases',
}

/** The types an item kind can use. */
export const EXERCISE_TYPES: Record<ItemKind, ExerciseType[]> = {
  entries: ['card.choice', 'card.handwriting', 'sentence.choice'],
  kanji: ['card.choice', 'card.handwriting'],
}

/**
 * What a handwriting card can ask to write, per item kind: the kanji, or a
 * word's spelling or reading. Mirrors HANDWRITING_ANSWERS in the backend.
 */
export const HANDWRITING_ANSWERS: Record<ItemKind, StudyField[]> = {
  entries: ['writing', 'reading'],
  kanji: ['literal'],
}

export function fieldItems(kind: ItemKind): { label: string; value: StudyField }[] {
  return STUDY_FIELDS[kind].map(field => ({ label: FIELD_LABELS[field], value: field }))
}

/** "Escritura + Lectura → Significado". */
export function directionLabel(direction: Direction): string {
  return `${direction.prompt.map(field => FIELD_LABELS[field]).join(' + ')} → ${FIELD_LABELS[direction.answer]}`
}

/** Two directions are the same if they show the same fields, in any order, and ask the same one. */
export function directionKey(direction: Direction): string {
  return `${[...direction.prompt].sort().join('+')}>${direction.answer}`
}

/** What a new exercise starts with: ask the meaning, show the reading(s) on the back. */
export function defaultChoiceSettings(kind: ItemKind): ChoiceCardSettings {
  return kind === 'entries'
    ? {
        type: 'card.choice',
        directions: [{ prompt: ['writing'], answer: 'meaning' }],
        back_fields: ['reading'],
        option_count: 4,
        distractor_source: 'collection',
      }
    : {
        type: 'card.choice',
        directions: [{ prompt: ['literal'], answer: 'meaning' }],
        back_fields: ['onyomi', 'kunyomi'],
        option_count: 4,
        distractor_source: 'collection',
      }
}

/**
 * The directions a sentence exercise offers (word exercises): fill the gap
 * with the meaning as a hint, and the highlighted word's reading or meaning.
 * Mirrors SentenceChoiceSettings in the backend.
 */
export const SENTENCE_DIRECTIONS: Direction[] = [
  { prompt: ['meaning'], answer: 'writing' },
  { prompt: ['writing'], answer: 'reading' },
  { prompt: ['writing'], answer: 'meaning' },
]

export const SENTENCE_DIRECTION_LABELS: Record<string, string> = {
  writing: 'Rellenar el hueco',
  reading: 'Lectura de la palabra',
  meaning: 'Significado de la palabra',
}

/** What a new sentence exercise starts with: fill the gap. */
export function defaultSentenceSettings(): SentenceChoiceSettings {
  return {
    type: 'sentence.choice',
    directions: [SENTENCE_DIRECTIONS[0]!],
    back_fields: ['reading'],
    option_count: 4,
    show_translation: false,
  }
}

/**
 * What a new handwriting exercise starts with: see the meaning, write the
 * kanji (readings on the back) or the word (its reading on the back).
 */
export function defaultHandwritingSettings(kind: ItemKind): HandwritingCardSettings {
  return kind === 'entries'
    ? { type: 'card.handwriting', directions: [{ prompt: ['meaning'], answer: 'writing' }], back_fields: ['reading'] }
    : { type: 'card.handwriting', directions: [{ prompt: ['meaning'], answer: 'literal' }], back_fields: ['onyomi', 'kunyomi'] }
}
