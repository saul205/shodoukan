import { describe, expect, it } from 'vitest'
import { accuracyPercent, formatDuration, formatResponseTime } from '../../app/utils/session-format'

describe('session format', () => {
  it('writes durations in seconds, minutes or hours', () => {
    const start = '2026-10-05T10:00:00Z'
    expect(formatDuration(start, '2026-10-05T10:00:45Z')).toBe('45 s')
    expect(formatDuration(start, '2026-10-05T10:12:10Z')).toBe('12 min')
    expect(formatDuration(start, '2026-10-05T11:05:00Z')).toBe('1 h 05 min')
  })

  it('writes response times and accuracy', () => {
    expect(formatResponseTime(2340)).toBe('2,3 s')
    expect(accuracyPercent(2, 3)).toBe(67)
    expect(accuracyPercent(0, 0)).toBeNull()
  })
})
