/** Side of the square KanjiVG draws in (its SVG viewBox is `0 0 109 109`). */
export const KANJIVG_SIZE = 109

/** KanjiVG's own stroke width, in its coordinates. */
export const KANJIVG_STROKE_WIDTH = 3

/** Where a stroke starts: the point of its path's leading `M` command. */
export function strokeStart(path: string): [number, number] {
  const match = path.match(/^\s*M\s*(-?[\d.]+)[\s,]*(-?[\d.]+)/i)
  return match ? [Number(match[1]), Number(match[2])] : [0, 0]
}
