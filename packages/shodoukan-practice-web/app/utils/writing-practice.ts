import type { PracticeEntry } from '~/models/practice'
import { entryHeadword, entryReading } from '~/utils/practice-text'

// Writing practice: what to draw, in which order and how. Nothing of it is
// stored; it's a warm-up before the exercises, or a review during them.

/** Guided: stroke by stroke over the model. Free: trace the model, or draw from memory. */
export type PracticeMode = 'guided' | 'guided-free' | 'free'

export const PRACTICE_MODES: { value: PracticeMode; label: string; description: string; icon: string }[] = [
  { value: 'guided', label: 'Guiado', description: 'Trazo a trazo, con animación.', icon: 'i-lucide-route' },
  { value: 'guided-free', label: 'Guiado y libre', description: 'Una vez guiado y luego libre.', icon: 'i-lucide-pen-line' },
  { value: 'free', label: 'Libre', description: 'Calcar el modelo, o de memoria.', icon: 'i-lucide-brush' },
]

export const DEFAULT_MODE: PracticeMode = 'guided-free'
export const DEFAULT_REPETITIONS = 2
export const MAX_REPETITIONS = 5

/**
 * What is written in one go: a kanji or a word of the library (by id, so
 * their own meanings show), or a bare character (a kana, or a kanji linked
 * without an id).
 */
export type PracticeItem =
  | { kind: 'kanji'; id: number }
  | { kind: 'entry'; id: number }
  | { kind: 'char'; text: string }

/** An item as it's written and shown. */
export interface PracticeText {
  text: string
  reading?: string
  meanings: string[]
}

/** How a guided character is going: strokes done of all, and the last miss's hint. */
export interface GuidedProgress {
  done: number
  total: number
  hint: string | null
  misses: number
}

/** One drawing of the practice: an item, guided or free. */
export interface PracticeStep {
  /** The item's place in the queue. */
  index: number
  guided: boolean
  /** Which free drawing of this item it is (1-based); 0 when guided. */
  repetition: number
}

/**
 * The drawings for `count` items: guided once per item, `repetitions` free
 * ones, or one then the other. All of an item's drawings come together.
 */
export function practiceSteps(count: number, mode: PracticeMode, repetitions: number): PracticeStep[] {
  return Array.from({ length: count }, (_, index) => {
    const steps: PracticeStep[] = []
    if (mode !== 'free') steps.push({ index, guided: true, repetition: 0 })
    if (mode !== 'guided') {
      for (let repetition = 1; repetition <= repetitions; repetition++) steps.push({ index, guided: false, repetition })
    }
    return steps
  }).flat()
}

/** The characters of `text`, each once, in order, without spaces. */
export function practiceChars(text: string): string[] {
  return [...new Set(Array.from(text).filter(char => char.trim()))]
}

/** The characters of a word, one cell each. */
export function wordChars(text: string): string[] {
  return Array.from(text)
}

/** Library ids from the query (`12,15`), each once, in order. */
export function parseIds(value: unknown): number[] {
  if (typeof value !== 'string') return []
  return [...new Set(value.split(',').map(Number).filter(id => Number.isInteger(id) && id > 0))]
}

export function formatIds(ids: number[]): string {
  return ids.join(',')
}

/**
 * How a library word is written, as its cards show it: the headword (its
 * first enabled spelling, okurigana included, or its reading) and the reading
 * above it. `null` for an entry with nothing to write.
 */
export function entryWriting(entry: PracticeEntry): Omit<PracticeText, 'meanings'> | null {
  const text = entryHeadword(entry)
  if (!text) return null
  const reading = entryReading(entry)
  return reading && reading !== text ? { text, reading } : { text }
}

/** Smallest side of a cell, in px, to draw a word's characters side by side. */
export const MIN_CELL = 120

export interface CellGrid {
  columns: number
  rows: number
  /** Side of each cell, in px. */
  size: number
}

/**
 * How to lay out `n` square cells in a `width` × `height` box, `gap` apart:
 * the number of columns that makes them largest (a row on a PC, two columns
 * on a phone held upright). `null` when they'd be smaller than `MIN_CELL`:
 * then one cell is drawn at a time.
 */
export function fitCells(n: number, width: number, height: number, gap: number): CellGrid | null {
  let best: CellGrid | null = null
  for (let columns = 1; columns <= n; columns++) {
    const rows = Math.ceil(n / columns)
    const size = Math.floor(Math.min((width - gap * (columns - 1)) / columns, (height - gap * (rows - 1)) / rows))
    if (!best || size > best.size) best = { columns, rows, size }
  }
  return best && best.size >= MIN_CELL ? best : null
}

export function parseMode(value: unknown): PracticeMode {
  return PRACTICE_MODES.some(mode => mode.value === value) ? (value as PracticeMode) : DEFAULT_MODE
}

export function parseRepetitions(value: unknown): number {
  const number = Number(value)
  return Number.isInteger(number) ? Math.min(Math.max(number, 1), MAX_REPETITIONS) : DEFAULT_REPETITIONS
}

/** A shuffled copy (Fisher–Yates). */
export function shuffled<T>(items: T[], random: () => number = Math.random): T[] {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j]!, copy[i]!]
  }
  return copy
}
