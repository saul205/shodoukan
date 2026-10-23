/** Side of the square KanjiVG draws in (its SVG viewBox is `0 0 109 109`). */
export const KANJIVG_SIZE = 109

/** KanjiVG's own stroke width, in its coordinates. */
export const KANJIVG_STROKE_WIDTH = 3

/** Where a stroke starts: the point of its path's leading `M` command. */
export function strokeStart(path: string): [number, number] {
  const match = path.match(/^\s*M\s*(-?[\d.]+)[\s,]*(-?[\d.]+)/i)
  return match ? [Number(match[1]), Number(match[2])] : [0, 0]
}

/** Margin drawn around KanjiVG's square, in its units: strokes may run a little outside it. */
export const KANJIVG_PADDING = 6

/** A point of a drawn stroke, in KanjiVG's space. */
export type StrokePoint = [number, number]

/**
 * SVG path of a drawn stroke, to render it like a KanjiVG stroke (unfilled,
 * round caps). A single point becomes a dot.
 */
export function pointsToPath(points: StrokePoint[]): string {
  if (!points.length) return ''
  const [first, ...rest] = points.map(([x, y]) => `${x},${y}`)
  return rest.length ? `M${first} L${rest.join(' ')}` : `M${first} l0,0`
}

/**
 * A drawn stroke with fewer points (Ramer–Douglas–Peucker: points within
 * `epsilon` of the line between their neighbours go), rounded to one decimal.
 * Keeps the ends; a tap stays one point.
 */
export function simplifyStroke(points: StrokePoint[], epsilon = 0.5): StrokePoint[] {
  const rounded = points
    .map(([x, y]) => [Math.round(x * 10) / 10, Math.round(y * 10) / 10] as StrokePoint)
    .filter((p, i, all) => i === 0 || p[0] !== all[i - 1]![0] || p[1] !== all[i - 1]![1])
  if (rounded.length < 3) return rounded
  return rdp(rounded, epsilon)
}

function rdp(points: StrokePoint[], epsilon: number): StrokePoint[] {
  const first = points[0]!
  const last = points[points.length - 1]!
  let furthest = 0
  let index = 0
  for (let i = 1; i < points.length - 1; i++) {
    const distance = distanceToLine(points[i]!, first, last)
    if (distance > furthest) {
      furthest = distance
      index = i
    }
  }
  if (furthest <= epsilon) return [first, last]
  return [...rdp(points.slice(0, index + 1), epsilon).slice(0, -1), ...rdp(points.slice(index), epsilon)]
}

function distanceToLine([x, y]: StrokePoint, [x1, y1]: StrokePoint, [x2, y2]: StrokePoint): number {
  const dx = x2 - x1
  const dy = y2 - y1
  const length = Math.hypot(dx, dy)
  if (length === 0) return Math.hypot(x - x1, y - y1)
  return Math.abs(dy * x - dx * y + x2 * y1 - y2 * x1) / length
}
