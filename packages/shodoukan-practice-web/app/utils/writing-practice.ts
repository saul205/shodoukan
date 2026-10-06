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

/** One drawing of the practice: a character, guided or free. */
export interface PracticeStep {
  /** The character's place in the queue. */
  index: number
  char: string
  guided: boolean
  /** Which free drawing of this character it is (1-based); 0 when guided. */
  repetition: number
}

/**
 * The drawings for `chars`: guided once per character, `repetitions` free
 * ones, or one then the other. All of a character's drawings come together.
 */
export function practiceSteps(chars: string[], mode: PracticeMode, repetitions: number): PracticeStep[] {
  return chars.flatMap((char, index) => {
    const steps: PracticeStep[] = []
    if (mode !== 'free') steps.push({ index, char, guided: true, repetition: 0 })
    if (mode !== 'guided') {
      for (let repetition = 1; repetition <= repetitions; repetition++) steps.push({ index, char, guided: false, repetition })
    }
    return steps
  })
}

/** The characters of `text`, each once, in order, without spaces. */
export function practiceChars(text: string): string[] {
  return [...new Set(Array.from(text).filter(char => char.trim()))]
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
