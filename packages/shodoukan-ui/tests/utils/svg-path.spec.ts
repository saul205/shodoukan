import { describe, expect, it } from 'vitest'
import { pathPoints } from '../../src/utils/svg-path'
import type { StrokePoint } from '../../src/utils/strokes'

// The same cases as the Python original's tests (tests/shodoukan/test_svg_path.py).
const gaps = (points: StrokePoint[]) =>
  points.slice(1).map((p, i) => Math.hypot(p[0] - points[i]![0], p[1] - points[i]![1]))

describe('pathPoints', () => {
  it('spaces a straight cubic evenly', () => {
    expect(pathPoints('M20,30c10,0,20,0,30,0', 5)).toEqual(Array.from({ length: 7 }, (_, i) => [20 + 5 * i, 30]))
  })

  it('keeps both ends of a curve, and the spacing', () => {
    const points = pathPoints('M54,10c0,5-20,20-40,25', 2)

    expect(points[0]).toEqual([54, 10])
    expect(points[points.length - 1]).toEqual([14, 35])
    for (const gap of gaps(points).slice(0, -1)) expect(gap).toBeCloseTo(2, 1)
  })

  it('reads a real KanjiVG stroke, with numbers not separated', () => {
    // 食's first stroke, as KanjiVG writes it.
    const points = pathPoints('M52.75,10.5c0.11,0.98-0.19,2.67-0.97,3.93C45,25.34,31.75,41.19,14,51.5')

    expect(points[0]).toEqual([52.75, 10.5])
    expect(points[points.length - 1]).toEqual([14, 51.5])
    expect(points.length).toBeGreaterThan(40)
  })

  it('reflects the previous control point on a smooth curve', () => {
    // The `s` segment mirrors the `c` one: a symmetric arch around x = 10.
    const points = pathPoints('M0,0c0,10,10,10,10,10s10,0,10,-10', 0.5)

    const top = points.reduce((a, b) => (b[1] > a[1] ? b : a))
    expect(Math.abs(top[0] - 10)).toBeLessThanOrEqual(0.5)
    expect(points[points.length - 1]).toEqual([20, 0])
  })

  it('reads lines and close', () => {
    const points = pathPoints('M0,0h3v4z', 1)

    expect(points[0]).toEqual([0, 0])
    expect(points[points.length - 1]).toEqual([0, 0])
    expect(points).toHaveLength(13) // 3 + 4 + 5 units of perimeter
  })

  it('yields the ends of a short path', () => {
    expect(pathPoints('M0,0L0.5,0', 2)).toEqual([[0, 0], [0.5, 0]])
    expect(pathPoints('M3,4')).toEqual([[3, 4]])
  })

  it.each(['M0,0A5,5,0,0,1,10,10', '0,0L1,1', 'M0'])('rejects unsupported path data %s', d => {
    expect(() => pathPoints(d)).toThrow()
  })
})
