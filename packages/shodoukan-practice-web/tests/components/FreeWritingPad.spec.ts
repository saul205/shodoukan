// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { KanjiDrawingPad, KanjiStrokeDiagram } from 'shodoukan-ui'
import FreeWritingPad from '../../app/components/FreeWritingPad.vue'
import { signedInAuth } from '../fakes'
import { stubResizeObserver } from '../resize-observer'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)
beforeEach(() => stubResizeObserver())
afterEach(() => vi.unstubAllGlobals())

const ICHI = [{ path: 'M14,54c20,0,60,0,80,0', label: null }]

describe('FreeWritingPad', () => {
  it('draws over the model, which can be hidden', async () => {
    const wrapper = await mountSuspended(FreeWritingPad, { props: { strokes: ICHI } })
    expect(wrapper.find('[data-model]').exists()).toBe(true)

    await wrapper.setProps({ showModel: false })

    expect(wrapper.find('[data-model]').exists()).toBe(false)
  })

  it('checks a drawing by laying it over the model, without a grade', async () => {
    const wrapper = await mountSuspended(FreeWritingPad, { props: { strokes: ICHI } })
    expect(wrapper.get('[data-testid="check"]').attributes('disabled')).toBeDefined()

    wrapper.findComponent(KanjiDrawingPad).vm.$emit('update:modelValue', [[[14, 54], [94, 54]]])
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="check"]').trigger('click')

    const result = wrapper.findComponent(KanjiStrokeDiagram)
    expect(result.props('ghost')).toEqual(ICHI)
    expect(result.props('strokes')).toEqual([{ path: 'M14,54 L94,54', label: [14, 54] }])
    expect(wrapper.get('[data-testid="free-status"]').text()).toBe('1 trazo · el modelo tiene 1')
    expect(wrapper.emitted('done')).toHaveLength(1)
  })
})
