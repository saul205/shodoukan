// @vitest-environment nuxt
import { afterEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { KanjiStrokeDiagram } from 'shodoukan-ui'
import FreeCell from '../../app/components/FreeCell.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)

const ICHI = [{ path: 'M14,54c20,0,60,0,80,0', label: null }]
const props = { strokes: ICHI, size: 200, showModel: true, checked: false }

describe('FreeCell', () => {
  it('draws over the model, which can be hidden, and says when it is touched', async () => {
    const wrapper = await mountSuspended(FreeCell, { props })
    expect(wrapper.find('[data-model]').exists()).toBe(true)

    await wrapper.get('[data-testid="drawing-pad"]').trigger('pointerdown')
    expect(wrapper.emitted('touch')).toHaveLength(1)

    await wrapper.setProps({ showModel: false })
    expect(wrapper.find('[data-model]').exists()).toBe(false)
  })

  it('once checked, lays the drawing over the model, with the stroke counts', async () => {
    const wrapper = await mountSuspended(FreeCell, {
      props: { ...props, checked: true, modelValue: [[[14, 54], [94, 54]]] },
    })

    const result = wrapper.findComponent(KanjiStrokeDiagram)
    expect(result.props('ghost')).toEqual(ICHI)
    expect(result.props('strokes')).toEqual([{ path: 'M14,54 L94,54', label: [14, 54] }])
    expect(wrapper.get('[data-testid="free-counts"]').text()).toBe('1 / 1 trazos')
  })
})
