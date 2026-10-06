import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import KanjiDrawingPad from '../../src/components/KanjiDrawingPad.vue'
import type { StrokePoint } from '../../src/utils/strokes'

// The pad is 121 px wide on screen and its viewBox is 121 units (-6 to 115),
// so a pixel is a unit: clientX 6 is x 0.
beforeEach(() => {
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
    left: 0, top: 0, width: 121, height: 121, right: 121, bottom: 121, x: 0, y: 0, toJSON: () => ({}),
  })
})
afterEach(() => vi.restoreAllMocks())

// jsdom has no PointerEvent: a mouse event with the pointer's own fields.
function pointer(type: string, x: number, y: number, init: { isPrimary?: boolean } = {}) {
  const event = new MouseEvent(type, { clientX: x, clientY: y, bubbles: true })
  return Object.assign(event, { pointerId: 1, isPrimary: init.isPrimary ?? true })
}

async function draw(wrapper: ReturnType<typeof mount>, points: [number, number][], init: { isPrimary?: boolean } = {}) {
  const svg = wrapper.get('svg').element
  const [first, ...rest] = points
  svg.dispatchEvent(pointer('pointerdown', first![0], first![1], init))
  for (const [x, y] of rest) svg.dispatchEvent(pointer('pointermove', x, y, init))
  const last = points[points.length - 1]!
  svg.dispatchEvent(pointer('pointerup', last[0], last[1], init))
  await wrapper.vm.$nextTick()
}

describe('KanjiDrawingPad', () => {
  it('adds each stroke, simplified, in KanjiVG units', async () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [] } })

    await draw(wrapper, [[16, 60], [36, 60], [56, 60.2], [96, 60]])

    const strokes = wrapper.emitted('update:modelValue')![0]![0] as StrokePoint[][]
    expect(strokes).toEqual([[[10, 54], [90, 54]]])
    expect(wrapper.emitted('stroke-end')![0]).toEqual([[[10, 54], [90, 54]]])
  })

  it('draws the strokes it holds', () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [[[10, 54], [90, 54]], [[50, 10]]] } })

    expect(wrapper.findAll('[data-stroke]').map(p => p.attributes('d'))).toEqual(['M10,54 L90,54', 'M50,10 l0,0'])
  })

  it('keeps points on the canvas', async () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [] } })

    await draw(wrapper, [[-50, 60], [500, 60]])

    expect(wrapper.emitted('update:modelValue')![0]![0]).toEqual([[[-6, 54], [115, 54]]])
  })

  it('ignores a second finger and a disabled pad', async () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [] } })
    await draw(wrapper, [[10, 10], [50, 50]], { isPrimary: false })
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()

    await wrapper.setProps({ disabled: true })
    await draw(wrapper, [[10, 10], [50, 50]])
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('undoes the last stroke and clears them all', async () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [[[1, 1]], [[2, 2]]] } })
    const pad = wrapper.vm as unknown as { undo: () => void; clear: () => void }

    pad.undo()
    pad.clear()

    expect(wrapper.emitted('update:modelValue')).toEqual([[[[[1, 1]]]], [[]]])
  })

  it('maps a box that isn\'t square as the drawing is fitted: centred, one scale', async () => {
    // 200 wide, 121 tall: the 121-unit drawing sits in the middle, 39.5 px in.
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
      left: 0, top: 0, width: 200, height: 121, right: 200, bottom: 121, x: 0, y: 0, toJSON: () => ({}),
    })
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [] } })

    await draw(wrapper, [[39.5, 0], [100, 60.5], [160.5, 121]])

    expect(wrapper.emitted('update:modelValue')![0]![0]).toEqual([[[-6, -6], [115, 115]]])
  })

  it('maps through the screen matrix when there is one', async () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [] } })
    const svg = wrapper.get('svg').element as SVGSVGElement
    // Drawn at twice the size, 100 px from the left: x = (clientX - 100) / 2 - 6.
    const inverse = { a: 0.5, b: 0, c: 0, d: 0.5, e: -56, f: -6 }
    Object.assign(svg, { getScreenCTM: () => ({ inverse: () => inverse }) })
    vi.stubGlobal('DOMPoint', class {
      constructor(public x: number, public y: number) {}
      matrixTransform(m: typeof inverse) {
        return { x: m.a * this.x + m.c * this.y + m.e, y: m.b * this.x + m.d * this.y + m.f }
      }
    })

    await draw(wrapper, [[112, 12], [292, 12]])

    expect(wrapper.emitted('update:modelValue')![0]![0]).toEqual([[[0, 0], [90, 0]]])
    vi.unstubAllGlobals()
  })
})

describe('KanjiDrawingPad limits', () => {
  beforeEach(() => {
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
      left: 0, top: 0, width: 121, height: 121, right: 121, bottom: 121, x: 0, y: 0, toJSON: () => ({}),
    })
  })

  it("doesn't start a stroke past maxStrokes, and says so", async () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [[[1, 1]]], maxStrokes: 1 } })

    await draw(wrapper, [[10, 10], [50, 50]])

    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.emitted('limit')).toHaveLength(1)
  })

  it('simplifies a stroke harder until it has at most maxPoints', async () => {
    const wrapper = mount(KanjiDrawingPad, { props: { modelValue: [], maxPoints: 5 } })
    // A zigzag: every point counts at the default epsilon.
    const zigzag = Array.from({ length: 40 }, (_, i) => [6 + i * 2, 60 + (i % 2) * 3] as [number, number])

    await draw(wrapper, zigzag)

    const [stroke] = wrapper.emitted('update:modelValue')![0]![0] as StrokePoint[][]
    expect(stroke!.length).toBeLessThanOrEqual(5)
    expect(stroke!.length).toBeGreaterThanOrEqual(2)
  })
})
