import type { Page } from 'shodoukan-ui'
import type {
  AnswerResult,
  ExerciseAnswer,
  ExerciseSession,
  SessionQuery,
  SessionSummary,
} from '../models/practice'
import type { ApiClient } from '../utils/api-client'

/**
 * Start studying an exercise: a new session with its first question. The
 * user's open session, of any exercise, is closed. `meaningLang` as the items
 * store it: "eng" for words, "en" for kanji.
 */
export function startSession(api: ApiClient, exerciseId: number, meaningLang: string): Promise<ExerciseSession> {
  return api<ExerciseSession>(`/exercises/${exerciseId}/sessions`, {
    method: 'POST',
    body: { meaning_lang: meaningLang },
  })
}

export function getSession(api: ApiClient, id: number): Promise<ExerciseSession> {
  return api<ExerciseSession>(`/exercise-sessions/${id}`)
}

/** Answer the active question; returns it graded and the next one. */
export function answerQuestion(
  api: ApiClient,
  sessionId: number,
  questionId: number,
  answer: ExerciseAnswer,
  responseMs: number,
): Promise<AnswerResult> {
  return api<AnswerResult>(`/exercise-sessions/${sessionId}/answer`, {
    method: 'POST',
    body: { question_id: questionId, answer, response_ms: responseMs },
  })
}

/** Idempotent; the active question, never answered, is dropped. */
export function finishSession(api: ApiClient, id: number): Promise<ExerciseSession> {
  return api<ExerciseSession>(`/exercise-sessions/${id}/finish`, { method: 'POST' })
}

/** The user's sessions, newest first, without their questions. */
export function listSessions(api: ApiClient, query: SessionQuery = {}): Promise<Page<SessionSummary>> {
  return api<Page<SessionSummary>>('/exercise-sessions', { query })
}
