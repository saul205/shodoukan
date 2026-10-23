// Flattens SVG path data into evenly spaced points: a port of
// `shodoukan.utils.svg_path`, so a stroke is sampled the same way here as in
// the practice backend's grader.
//
// KanjiVG draws each stroke as the centre line of a pen stroke, with `M`, `C`
// and `S` commands (absolute and relative). Lines (`L`, `H`, `V`) and `Z` are
// read too, so any simple open path works. Arcs and quadratic curves aren't.

import type { StrokePoint } from './strokes'

// A command letter, or a number (KanjiVG writes "2.67-0.97" and ".5.5" without
// separators).
const TOKEN = /[MmCcSsLlHhVvZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?/g
// Samples per cubic segment before resampling: plenty for strokes of a 109 square.
const CURVE_SAMPLES = 24

/**
 * The points of path `d`, `spacing` apart along it (in the path's units).
 *
 * The first and last points of the path are always kept, so a path shorter
 * than `spacing` yields its two ends. Throws for path data it can't read.
 */
export function pathPoints(d: string, spacing = 1): StrokePoint[] {
  if (spacing <= 0) throw new Error('spacing must be positive')
  const line = polyline(d)
  if (!line.length) return []
  const round = (value: number) => Math.round(value * 100) / 100
  return resample(line, spacing).map(([x, y]) => [round(x), round(y)])
}

function polyline(d: string): StrokePoint[] {
  const tokens = d.match(TOKEN) ?? []
  if (tokens.join('') !== d.replace(/[\s,]/g, '')) throw new Error(`unsupported path data: ${d}`)
  const points: StrokePoint[] = []
  let current: StrokePoint = [0, 0]
  let start: StrokePoint = [0, 0]
  // The second control point of the last cubic, reflected by `S`.
  let lastControl: StrokePoint | null = null
  let command = ''
  let i = 0
  const isCommand = (token: string) => /^[a-z]$/i.test(token)

  function numbers(count: number): number[] {
    const values = tokens.slice(i, i + count)
    if (values.length < count || values.some(isCommand)) throw new Error(`missing coordinates in path data: ${d}`)
    i += count
    return values.map(Number)
  }

  while (i < tokens.length) {
    if (isCommand(tokens[i]!)) {
      command = tokens[i]!
      i++
    } else if (!command) {
      throw new Error(`path data must start with a command: ${d}`)
    }
    const relative = command === command.toLowerCase()
    const [ox, oy] = relative ? current : [0, 0]
    const kind = command.toUpperCase()

    if (kind === 'M') {
      const [x, y] = numbers(2) as [number, number]
      current = start = [ox + x, oy + y]
      points.push(current)
      lastControl = null
      // Further pairs after a move are implicit line-tos.
      command = relative ? 'l' : 'L'
    } else if (kind === 'L') {
      const [x, y] = numbers(2) as [number, number]
      current = [ox + x, oy + y]
      points.push(current)
      lastControl = null
    } else if (kind === 'H') {
      const [x] = numbers(1) as [number]
      current = [ox + x, current[1]]
      points.push(current)
      lastControl = null
    } else if (kind === 'V') {
      const [y] = numbers(1) as [number]
      current = [current[0], oy + y]
      points.push(current)
      lastControl = null
    } else if (kind === 'C' || kind === 'S') {
      let c1: StrokePoint
      let x2: number, y2: number, x: number, y: number
      if (kind === 'C') {
        const [x1, y1, ...rest] = numbers(6) as [number, number, number, number, number, number]
        ;[x2, y2, x, y] = rest as [number, number, number, number]
        c1 = [ox + x1, oy + y1]
      } else {
        ;[x2, y2, x, y] = numbers(4) as [number, number, number, number]
        c1 = lastControl ? [2 * current[0] - lastControl[0], 2 * current[1] - lastControl[1]] : current
      }
      const c2: StrokePoint = [ox + x2, oy + y2]
      const end: StrokePoint = [ox + x, oy + y]
      points.push(...cubic(current, c1, c2, end))
      current = end
      lastControl = c2
    } else {
      // Z: TOKEN only matches the commands above.
      current = start
      points.push(current)
      lastControl = null
      command = ''
    }
  }
  return points
}

/** Points along a cubic Bézier, without its start (already in the line). */
function cubic(p0: StrokePoint, p1: StrokePoint, p2: StrokePoint, p3: StrokePoint): StrokePoint[] {
  const result: StrokePoint[] = []
  for (let step = 1; step <= CURVE_SAMPLES; step++) {
    const t = step / CURVE_SAMPLES
    const u = 1 - t
    const [a, b, c, e] = [u ** 3, 3 * u * u * t, 3 * u * t * t, t ** 3]
    result.push([a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]])
  }
  return result
}

/** Points `spacing` apart along the polyline, plus its last point. */
function resample(line: StrokePoint[], spacing: number): StrokePoint[] {
  const result: StrokePoint[] = [line[0]!]
  let carried = 0 // length walked since the last emitted point
  for (let k = 1; k < line.length; k++) {
    const [x0, y0] = line[k - 1]!
    const [x1, y1] = line[k]!
    const length = Math.hypot(x1 - x0, y1 - y0)
    if (length === 0) continue
    let walked = spacing - carried
    while (walked <= length) {
      const t = walked / length
      result.push([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t])
      walked += spacing
    }
    carried = length - (walked - spacing)
  }
  const last = line[line.length - 1]!
  const emitted = result[result.length - 1]!
  if ((emitted[0] !== last[0] || emitted[1] !== last[1]) && (result.length === 1 || carried > 1e-9)) result.push(last)
  return result
}
