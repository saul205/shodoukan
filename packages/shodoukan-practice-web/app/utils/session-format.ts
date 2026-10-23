// How sessions are written in the UI (Spanish, the user's time zone).

const dateTime = new Intl.DateTimeFormat('es', { dateStyle: 'medium', timeStyle: 'short' })

/** "5 oct 2026, 10:30". */
export function formatDateTime(iso: string): string {
  return dateTime.format(new Date(iso))
}

/** From `start` to `end`: "45 s", "12 min", "1 h 05 min". */
export function formatDuration(start: string, end: string): string {
  const seconds = Math.max(0, Math.round((Date.parse(end) - Date.parse(start)) / 1000))
  if (seconds < 60) return `${seconds} s`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min`
  return `${Math.floor(minutes / 60)} h ${String(minutes % 60).padStart(2, '0')} min`
}

/** A response time: "2,3 s". */
export function formatResponseTime(ms: number): string {
  return `${(ms / 1000).toLocaleString('es', { maximumFractionDigits: 1 })} s`
}

/** Right answers as a whole percentage; null with no answers. */
export function accuracyPercent(score: number, answered: number): number | null {
  return answered ? Math.round((score / answered) * 100) : null
}
