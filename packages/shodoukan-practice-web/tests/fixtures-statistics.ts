import type { AnswerTotals, MissedItem, PracticeStatistics } from '../app/models/practice'

export function totals(overrides: Partial<AnswerTotals> = {}): AnswerTotals {
  return { sessions: 3, answered: 20, correct: 15, accuracy: 0.75, mean_response_ms: 2300, ...overrides }
}

export function missed(item_id: number, label: string, reading: string | null = null): MissedItem {
  return { item_id, label, reading, answered: 4, wrong: 3 }
}

export function practiceStatistics(overrides: Partial<PracticeStatistics> = {}): PracticeStatistics {
  return {
    totals: totals(),
    activity: [
      { day: '2026-10-03', answered: 0, correct: 0 },
      { day: '2026-10-04', answered: 10, correct: 5 },
      { day: '2026-10-05', answered: 20, correct: 15 },
    ],
    exercises: [{
      exercise_id: 2,
      exercise_name: 'N5',
      item_kind: 'kanji',
      sessions: 3,
      answered: 20,
      correct: 15,
      accuracy: 0.75,
      last_answered_at: '2026-10-05T10:00:00Z',
    }],
    most_missed_entries: [missed(1, '食べる', 'たべる')],
    most_missed_kanji: [missed(7, '食'), missed(8, '水')],
    ...overrides,
  }
}
