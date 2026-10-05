import type { ExerciseStatistics, PracticeStatistics } from '../models/practice'
import type { ApiClient } from '../utils/api-client'

/** How the user does in one exercise. */
export function getExerciseStatistics(api: ApiClient, exerciseId: number): Promise<ExerciseStatistics> {
  return api<ExerciseStatistics>(`/exercises/${exerciseId}/statistics`)
}

/**
 * How the user does overall, with the answers of each of the last `days`
 * days (1–365) counted in the IANA time zone `tz`.
 */
export function getPracticeStatistics(api: ApiClient, days: number, tz: string): Promise<PracticeStatistics> {
  return api<PracticeStatistics>('/statistics', { query: { days, tz } })
}
