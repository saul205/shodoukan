import type { Exercise, ExerciseInput, NewExerciseInput } from '../models/practice'
import type { ApiClient } from '../utils/api-client'

/** The user's exercises, sorted by name. */
export function listExercises(api: ApiClient): Promise<Exercise[]> {
  return api<Exercise[]>('/exercises')
}

export function getExercise(api: ApiClient, id: number): Promise<Exercise> {
  return api<Exercise>(`/exercises/${id}`)
}

export function createExercise(api: ApiClient, input: NewExerciseInput): Promise<Exercise> {
  return api<Exercise>('/exercises', { method: 'POST', body: input })
}

/** Replaces every editable field; the item kind can't change. */
export function updateExercise(api: ApiClient, id: number, input: ExerciseInput): Promise<Exercise> {
  return api<Exercise>(`/exercises/${id}`, { method: 'PUT', body: input })
}

/** Its past sessions are kept. */
export function deleteExercise(api: ApiClient, id: number): Promise<void> {
  return api(`/exercises/${id}`, { method: 'DELETE' })
}
