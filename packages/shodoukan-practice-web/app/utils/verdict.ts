import type { ExerciseQuestion, StrokeFeedback, StrokeStatus } from '~/models/practice'

// How an answered question went, shared by the players and the review. A
// drawing graded "close" counts as right but is shown apart: "Mejorable".

export type QuestionVerdict = 'correct' | 'close' | 'wrong' | 'skipped'

export const VERDICT_COLORS: Record<QuestionVerdict, 'success' | 'warning' | 'error'> = {
  correct: 'success',
  close: 'warning',
  wrong: 'error',
  skipped: 'warning',
}

/** The verdict as a short label (the review's badges). */
export const VERDICT_LABELS: Record<QuestionVerdict, string> = {
  correct: 'Correcta',
  close: 'Mejorable',
  wrong: 'Fallada',
  skipped: 'Saltada',
}

export function verdictOf(question: ExerciseQuestion): QuestionVerdict {
  if (question.answer?.type === 'skip') return 'skipped'
  if (question.type === 'card.handwriting' && question.grade?.verdict === 'close') return 'close'
  return question.is_correct ? 'correct' : 'wrong'
}

export const STROKE_STATUS_COLORS: Record<StrokeStatus, string | undefined> = {
  ok: 'var(--ui-success)',
  reversed: 'var(--ui-warning)',
  out_of_order: 'var(--ui-warning)',
  imprecise: 'var(--ui-warning)',
  extra: 'var(--ui-error)',
  missing: 'var(--ui-error)',
}

/** What's wrong with a stroke, in a sentence; `null` for a right one. */
export function strokeProblem(feedback: StrokeFeedback): string | null {
  const drawn = feedback.drawn !== null ? feedback.drawn + 1 : null
  const reference = feedback.reference !== null ? feedback.reference + 1 : null
  switch (feedback.status) {
    case 'ok':
      return null
    case 'reversed':
      return `Trazo ${drawn}: en sentido contrario.`
    case 'out_of_order':
      return `Trazo ${drawn}: fuera de orden (es el ${reference}.º).`
    case 'imprecise':
      return `Trazo ${drawn}: poco preciso.`
    case 'extra':
      return `Trazo ${drawn}: sobra.`
    case 'missing':
      return `Falta el trazo ${reference}.`
  }
}
