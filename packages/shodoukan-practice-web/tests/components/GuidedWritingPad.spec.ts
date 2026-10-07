// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { KanjiDrawingPad, type StrokePoint } from 'shodoukan-ui'
import GuidedWritingPad from '../../app/components/GuidedWritingPad.vue'
import { signedInAuth } from '../fakes'
import { stubResizeObserver } from '../resize-observer'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)
beforeEach(() => stubResizeObserver())
afterEach(() => vi.unstubAllGlobals())

// 二: a short stroke on top, a long one below, both left to right.
const NI = [
  { path: 'M30,35c15,0,35,0,50,0', label: null },
  { path: 'M14,75c20,0,60,0,80,0', label: null },
]
const TOP: StrokePoint[] = [[31, 36], [55, 35], [79, 34]]
const BOTTOM: StrokePoint[] = [[15, 76], [54, 75], [93, 74]]

async function trace(wrapper: Awaited<ReturnType<typeof mountSuspended>>, stroke: StrokePoint[]) {
  const pad = wrapper.findComponent(KanjiDrawingPad)
  pad.vm.$emit('update:modelValue', [stroke])
  pad.vm.$emit('stroke-end', stroke)
  await wrapper.vm.$nextTick()
}

const status = (wrapper: Awaited<ReturnType<typeof mountSuspended>>) =>
  wrapper.get('[data-testid="guided-status"]').text()

describe('GuidedWritingPad', () => {
  it('shows the model, and animates the first stroke from a red dot', async () => {
    const wrapper = await mountSuspended(GuidedWritingPad, { props: { strokes: NI } })

    expect(wrapper.findAll('[data-model]')).toHaveLength(2)
    expect(wrapper.get('[data-current]').attributes('d')).toBe(NI[0]!.path)
    expect(wrapper.get('[data-start]').attributes()).toMatchObject({ cx: '30', cy: '35' })
    expect(status(wrapper)).toBe('Trazo 1 de 2')
  })

  it('turns a stroke that follows the model into the model, then the next', async () => {
    const wrapper = await mountSuspended(GuidedWritingPad, { props: { strokes: NI } })

    await trace(wrapper, TOP)

    expect(wrapper.findAll('[data-done]').map(p => p.attributes('d'))).toEqual([NI[0]!.path])
    expect(wrapper.get('[data-current]').attributes('d')).toBe(NI[1]!.path)
    expect(wrapper.findComponent(KanjiDrawingPad).props('modelValue')).toEqual([])
    expect(status(wrapper)).toBe('Trazo 2 de 2')

    await trace(wrapper, BOTTOM)

    expect(wrapper.emitted('done')).toHaveLength(1)
    expect(status(wrapper)).toBe('¡Hecho!')
  })

  it('wipes a stroke that misses, with a hint', async () => {
    const wrapper = await mountSuspended(GuidedWritingPad, { props: { strokes: NI } })

    await trace(wrapper, BOTTOM)
    expect(status(wrapper)).toBe('Empieza en el punto rojo.')
    expect(wrapper.findAll('[data-done]')).toHaveLength(0)
    expect(wrapper.findComponent(KanjiDrawingPad).props('modelValue')).toEqual([])

    await trace(wrapper, [...TOP].reverse())
    expect(status(wrapper)).toBe('Al revés: empieza en el punto rojo.')
  })

  it('lets a stroke be skipped after three misses', async () => {
    const wrapper = await mountSuspended(GuidedWritingPad, { props: { strokes: NI } })
    const skip = () => wrapper.get('[data-testid="skip-stroke"]')

    for (let i = 0; i < 2; i++) await trace(wrapper, BOTTOM)
    expect(skip().attributes('disabled')).toBeDefined()
    await trace(wrapper, BOTTOM)
    await skip().trigger('click')

    expect(status(wrapper)).toBe('Trazo 2 de 2')
  })

  it('undoes a stroke and starts over', async () => {
    const wrapper = await mountSuspended(GuidedWritingPad, { props: { strokes: NI } })
    await trace(wrapper, TOP)

    await wrapper.get('[data-testid="undo"]').trigger('click')
    expect(status(wrapper)).toBe('Trazo 1 de 2')

    await trace(wrapper, TOP)
    await wrapper.get('[data-testid="restart"]').trigger('click')
    expect(wrapper.findAll('[data-done]')).toHaveLength(0)
  })
})
