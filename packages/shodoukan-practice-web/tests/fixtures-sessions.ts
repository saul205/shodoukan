import type { ExerciseQuestion, ExerciseSession } from '../app/models/practice'

/** An unanswered kanji question (literal → kun'yomi); option 0 is right. */
export function question(id: number, literal = '食'): ExerciseQuestion {
  return {
    type: 'card.choice',
    id,
    position: id - 1,
    prompt_fields: ['literal'],
    answer_field: 'kunyomi',
    prompt: [{ field: 'literal', values: [literal] }],
    options: ['た.べる', 'みず', 'ひ', 'やま'].map(text => ({ text, item_id: null })),
    answered: false,
    item_id: null,
    correct_option: null,
    back: null,
    answer: null,
    is_correct: null,
    answered_at: null,
    response_ms: null,
  }
}

/** `question` answered with `option`, with its solution. */
export function graded(unanswered: ExerciseQuestion, option: number): ExerciseQuestion {
  return {
    ...unanswered,
    options: unanswered.options.map((o, i) => ({ ...o, item_id: 10 + i })),
    answered: true,
    item_id: 10,
    correct_option: 0,
    back: [...unanswered.prompt, { field: 'kunyomi', values: ['た.べる'] }],
    answer: { type: 'option', option },
    is_correct: option === 0,
    answered_at: '2026-10-05T10:00:00Z',
    response_ms: 1200,
  }
}

export function session(overrides: Partial<ExerciseSession> = {}): ExerciseSession {
  return {
    id: 5,
    exercise_id: 2,
    exercise_name: 'N5',
    item_kind: 'kanji',
    meaning_lang: 'en',
    started_at: '2026-10-05T09:00:00Z',
    last_activity_at: '2026-10-05T09:00:00Z',
    finished_at: null,
    answered: 0,
    score: 0,
    current: question(1),
    history: [],
    ...overrides,
  }
}
