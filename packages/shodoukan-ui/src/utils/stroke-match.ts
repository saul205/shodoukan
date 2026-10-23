// Whether a stroke traced over a model follows one of its strokes, for guided
// writing practice. A simplified take on the practice backend's grader
// (`handwriting_grading_service._pair`): the same stroke distance, but in
// absolute KanjiVG units instead of normalised by the drawing's box, since the
// stroke is traced on the same canvas as the model. It only checks one stroke
// at a time, against the one expected next.

import { pathPoints } from './svg-path'
import { KANJIVG_SIZE, type StrokePoint } from './strokes'

/** Points each stroke is resampled to before comparing. */
const SAMPLES = 16

/**
 * Largest distance, as a share of KanjiVG's square (about 13 units), at which
 * a traced stroke counts as the model's.
 */
export const GUIDED_STROKE_MATCH = 0.12

export interface StrokeMatch {
  /** The stroke follows the reference, in the right direction. */
  ok: boolean
  /** It follows the reference, but drawn from its end to its start. */
  reversed: boolean
  /** How far it is from the reference, as a share of the square (0 is exact). */
  distance: number
}

/** How the drawn stroke compares with the reference stroke `path`. */
export function matchStroke(drawn: StrokePoint[], path: string): StrokeMatch {
  const reference = resampleEvenly(pathPoints(path, 1), SAMPLES)
  const stroke = resampleEvenly(drawn, SAMPLES)
  if (!reference.length || !stroke.length) return { ok: false, reversed: false, distance: Infinity }
  const forward = strokeDistance(stroke, reference)
  const backward = strokeDistance([...stroke].reverse(), reference)
  const reversed = backward < forward && backward <= GUIDED_STROKE_MATCH
  return { ok: !reversed && forward <= GUIDED_STROKE_MATCH, reversed, distance: Math.min(forward, backward) }
}

/**
 * The backend's stroke distance: the mean distance between matching points
 * and the larger of the two end-point distances, averaged, in square shares.
 */
function strokeDistance(a: StrokePoint[], b: StrokePoint[]): number {
  const gap = (p: StrokePoint, q: StrokePoint) => Math.hypot(p[0] - q[0], p[1] - q[1])
  const mean = a.reduce((sum, p, i) => sum + gap(p, b[i]!), 0) / a.length
  const ends = Math.max(gap(a[0]!, b[0]!), gap(a[a.length - 1]!, b[b.length - 1]!))
  return (mean + ends) / 2 / KANJIVG_SIZE
}

/** `count` points evenly spaced along the polyline, both ends included. */
function resampleEvenly(line: StrokePoint[], count: number): StrokePoint[] {
  if (line.length <= 1) return line.length ? Array.from({ length: count }, () => line[0]!) : []
  const cumulative = [0]
  for (let i = 1; i < line.length; i++) {
    cumulative.push(cumulative[i - 1]! + Math.hypot(line[i]![0] - line[i - 1]![0], line[i]![1] - line[i - 1]![1]))
  }
  const total = cumulative[cumulative.length - 1]!
  if (total === 0) return Array.from({ length: count }, () => line[0]!)
  const result: StrokePoint[] = []
  let segment = 1
  for (let k = 0; k < count; k++) {
    const target = (total * k) / (count - 1)
    while (segment < line.length - 1 && cumulative[segment]! < target) segment++
    const [x0, y0] = line[segment - 1]!
    const [x1, y1] = line[segment]!
    const span = cumulative[segment]! - cumulative[segment - 1]!
    const t = span ? (target - cumulative[segment - 1]!) / span : 0
    result.push([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t])
  }
  return result
}
