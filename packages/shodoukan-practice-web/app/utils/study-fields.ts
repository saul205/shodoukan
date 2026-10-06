import type { ChoiceCardSettings, Direction, ExerciseType, HandwritingCardSettings, ItemKind, StudyField } from '~/models/practice'

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
  'card.handwriting': 'Escribir el kanji',
}

/** The types an item kind can use: drawing is for kanji only. */
export const EXERCISE_TYPES: Record<ItemKind, ExerciseType[]> = {
  entries: ['card.choice'],
  kanji: ['card.choice', 'card.handwriting'],
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

/** What a new handwriting exercise starts with: see the meaning, draw the kanji, readings on the back. */
export function defaultHandwritingSettings(): HandwritingCardSettings {
  return {
    type: 'card.handwriting',
    directions: [{ prompt: ['meaning'], answer: 'literal' }],
    back_fields: ['onyomi', 'kunyomi'],
  }
}
