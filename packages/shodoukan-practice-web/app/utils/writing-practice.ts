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

/** What is written in one go: a character, or a word one character after another. */
export interface PracticeItem {
  text: string
  /** A word's reading, shown with it. */
  reading?: string
}

/** One drawing of the practice: an item, guided or free. */
export interface PracticeStep {
  /** The item's place in the queue. */
  index: number
  text: string
  guided: boolean
  /** Which free drawing of this character it is (1-based); 0 when guided. */
  repetition: number
}

/**
 * The drawings for `texts`: guided once per item, `repetitions` free ones, or
 * one then the other. All of an item's drawings come together.
 */
export function practiceSteps(texts: string[], mode: PracticeMode, repetitions: number): PracticeStep[] {
  return texts.flatMap((text, index) => {
    const steps: PracticeStep[] = []
    if (mode !== 'free') steps.push({ index, text, guided: true, repetition: 0 })
    if (mode !== 'guided') {
      for (let repetition = 1; repetition <= repetitions; repetition++) steps.push({ index, text, guided: false, repetition })
    }
    return steps
  })
}

/** The characters of `text`, each once, in order, without spaces. */
export function practiceChars(text: string): string[] {
  return [...new Set(Array.from(text).filter(char => char.trim()))]
}

/** The characters of a word, one cell each. */
export function wordChars(text: string): string[] {
  return Array.from(text)
}

// Words travel in the query as `食べる:たべる,飲む:のむ` (the reading is optional):
// neither separator is used in Japanese writing.

/** Words from the query, each once, in order. */
export function parseWords(value: unknown): PracticeItem[] {
  if (typeof value !== 'string') return []
  const seen = new Set<string>()
  const items: PracticeItem[] = []
  for (const part of value.split(',')) {
    const [text = '', reading] = part.split(':').map(s => s.trim())
    if (!text || seen.has(text)) continue
    seen.add(text)
    items.push(reading ? { text, reading } : { text })
  }
  return items
}

export function formatWords(items: PracticeItem[]): string {
  return items.map(item => (item.reading && item.reading !== item.text ? `${item.text}:${item.reading}` : item.text)).join(',')
}

/**
 * How a library word is written, as its cards show it: the headword (its
 * first enabled spelling, okurigana included, or its reading) and the reading
 * above it. `null` for an entry with nothing to write.
 */
export function entryWriting(entry: PracticeEntry): PracticeItem | null {
  const text = entryHeadword(entry)
  if (!text) return null
  const reading = entryReading(entry)
  return reading && reading !== text ? { text, reading } : { text }
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
