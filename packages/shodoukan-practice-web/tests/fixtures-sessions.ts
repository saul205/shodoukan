import type { ChoiceQuestion, ExerciseSession, HandwritingGrade, HandwritingQuestion } from '../app/models/practice'

/** An unanswered kanji question (literal → kun'yomi); option 0 is right. */
export function question(id: number, literal = '食'): ChoiceQuestion {
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
export function graded(unanswered: ChoiceQuestion, option: number): ChoiceQuestion {
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

/** An unanswered handwriting question (meaning → kanji). */
export function drawingQuestion(id: number): HandwritingQuestion {
  return {
    type: 'card.handwriting',
    id,
    position: id - 1,
    prompt_fields: ['meaning'],
    answer_field: 'literal',
    prompt: [{ field: 'meaning', values: ['one'] }],
    answered: false,
    item_id: null,
    back: null,
    answer: null,
    is_correct: null,
    answered_at: null,
    response_ms: null,
    references: null,
    grade: null,
  }
}

/** `drawingQuestion` drawn with one stroke and graded `verdict` against 一. */
export function drawn(
  unanswered: HandwritingQuestion,
  verdict: HandwritingGrade['verdict'] = 'correct',
): HandwritingQuestion {
  return {
    ...unanswered,
    answered: true,
    item_id: 10,
    back: [...unanswered.prompt, { field: 'literal', values: ['一'] }],
    answer: { type: 'strokes', strokes: [[[10, 54], [90, 52]]] },
    is_correct: verdict !== 'wrong',
    answered_at: '2026-10-05T10:00:00Z',
    response_ms: 4200,
    references: [{ literal: '一', strokes: [{ path: 'M11,54.25c20,0,50,-4,78,-4', label: [4.25, 50.5] }] }],
    grade: {
      score: { correct: 92, close: 71, wrong: 18 }[verdict],
      verdict,
      matched: '一',
      strokes: [{ drawn: 0, reference: 0, status: verdict === 'correct' ? 'ok' : 'reversed' }],
    },
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
