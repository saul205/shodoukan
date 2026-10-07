// @vitest-environment nuxt
import { afterEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { KanjiDrawingPad, type StrokePoint } from 'shodoukan-ui'
import GuidedCell from '../../app/components/GuidedCell.vue'
import type { GuidedProgress } from '../../app/utils/writing-practice'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)

// 二: a short stroke on top, a long one below, both left to right.
const NI = [
  { path: 'M30,35c15,0,35,0,50,0', label: null },
  { path: 'M14,75c20,0,60,0,80,0', label: null },
]
const TOP: StrokePoint[] = [[31, 36], [55, 35], [79, 34]]
const BOTTOM: StrokePoint[] = [[15, 76], [54, 75], [93, 74]]

type Wrapper = Awaited<ReturnType<typeof mountSuspended>>

async function trace(wrapper: Wrapper, stroke: StrokePoint[]) {
  const pad = wrapper.findComponent(KanjiDrawingPad)
  pad.vm.$emit('update:modelValue', [stroke])
  pad.vm.$emit('stroke-end', stroke)
  await wrapper.vm.$nextTick()
}

const last = (wrapper: Wrapper) => (wrapper.emitted('progress') as [GuidedProgress][]).at(-1)![0]

describe('GuidedCell', () => {
  it('shows the model, and animates the first stroke from a red dot', async () => {
    const wrapper = await mountSuspended(GuidedCell, { props: { strokes: NI, size: 200 } })

    expect(wrapper.findAll('[data-model]')).toHaveLength(2)
    expect(wrapper.get('[data-current]').attributes('d')).toBe(NI[0]!.path)
    expect(wrapper.get('[data-start]').attributes()).toMatchObject({ cx: '30', cy: '35' })
    expect(last(wrapper)).toEqual({ done: 0, total: 2, hint: null, misses: 0 })
  })

  it('turns a stroke that follows the model into the model, then the next', async () => {
    const wrapper = await mountSuspended(GuidedCell, { props: { strokes: NI, size: 200 } })

    await trace(wrapper, TOP)

    expect(wrapper.findAll('[data-done]').map(p => p.attributes('d'))).toEqual([NI[0]!.path])
    expect(wrapper.get('[data-current]').attributes('d')).toBe(NI[1]!.path)
    expect(wrapper.findComponent(KanjiDrawingPad).props('modelValue')).toEqual([])
    expect(last(wrapper).done).toBe(1)

    await trace(wrapper, BOTTOM)

    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('wipes a stroke that misses, with a hint', async () => {
    const wrapper = await mountSuspended(GuidedCell, { props: { strokes: NI, size: 200 } })

    await trace(wrapper, BOTTOM)
    expect(last(wrapper)).toMatchObject({ done: 0, hint: 'Empieza en el punto rojo.', misses: 1 })
    expect(wrapper.findComponent(KanjiDrawingPad).props('modelValue')).toEqual([])

    await trace(wrapper, [...TOP].reverse())
    expect(last(wrapper).hint).toBe('Al revés: empieza en el punto rojo.')
  })

  it('skips, undoes and restarts', async () => {
    const wrapper = await mountSuspended(GuidedCell, { props: { strokes: NI, size: 200 } })
    const cell = wrapper.vm as unknown as { skip: () => void; undo: () => void; restart: () => void }

    cell.skip()
    await wrapper.vm.$nextTick()
    expect(last(wrapper).done).toBe(1)
    cell.undo()
    await wrapper.vm.$nextTick()
    expect(last(wrapper).done).toBe(0)
    await trace(wrapper, TOP)
    cell.restart()
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('[data-done]')).toHaveLength(0)
  })
})
