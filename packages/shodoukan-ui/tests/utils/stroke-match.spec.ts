import { describe, expect, it } from 'vitest'
import { matchStroke } from '../../src/utils/stroke-match'
import type { StrokePoint } from '../../src/utils/strokes'

// 一: one horizontal stroke across the middle, left to right.
const ICHI = 'M14,54c20,0,60,0,80,0'
const line = (from: StrokePoint, to: StrokePoint, steps = 10): StrokePoint[] =>
  Array.from({ length: steps + 1 }, (_, i) => [
    from[0] + ((to[0] - from[0]) * i) / steps,
    from[1] + ((to[1] - from[1]) * i) / steps,
  ])

describe('matchStroke', () => {
  it('accepts a stroke traced close to the model', () => {
    const result = matchStroke(line([16, 57], [91, 52]), ICHI)

    expect(result).toMatchObject({ ok: true, reversed: false })
    expect(result.distance).toBeLessThan(0.05)
  })

  it('accepts a slightly shaky stroke', () => {
    const shaky = line([12, 54], [96, 54], 20).map(([x, y], i) => [x, y + (i % 2 ? 4 : -4)] as StrokePoint)

    expect(matchStroke(shaky, ICHI).ok).toBe(true)
  })

  it('flags a stroke drawn backwards', () => {
    expect(matchStroke(line([94, 54], [14, 54]), ICHI)).toMatchObject({ ok: false, reversed: true })
  })

  it('rejects a stroke somewhere else', () => {
    expect(matchStroke(line([14, 90], [94, 90]), ICHI)).toMatchObject({ ok: false, reversed: false })
  })

  it('rejects half a stroke', () => {
    expect(matchStroke(line([14, 54], [54, 54]), ICHI).ok).toBe(false)
  })

  it('rejects a stroke the other way round (vertical)', () => {
    expect(matchStroke(line([54, 14], [54, 94]), ICHI).ok).toBe(false)
  })

  it('handles a tap and an empty stroke', () => {
    expect(matchStroke([[54, 54]], ICHI).ok).toBe(false)
    expect(matchStroke([], ICHI)).toEqual({ ok: false, reversed: false, distance: Infinity })
  })
})
