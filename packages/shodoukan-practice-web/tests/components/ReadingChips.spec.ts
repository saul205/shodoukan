// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import ReadingChips from '../../app/components/ReadingChips.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

const readings = [
  { id: 1, text: 'あに', enabled: true },
  { id: 2, text: 'このかみ', enabled: false },
]

// UTooltip needs the TooltipProvider that UApp gives the real app.
async function mountChips(props: Record<string, unknown>) {
  const wrapper = await mountSuspended(defineComponent({
    render: () => h(UApp, null, { default: () => h(ReadingChips, props) }),
  }))
  return {
    chips: () => wrapper.findAll('button'),
    emitted: () => wrapper.findComponent(ReadingChips).emitted('toggle'),
  }
}

describe('ReadingChips', () => {
  it('shows hidden readings faded and struck through, with aria-pressed', async () => {
    const { chips } = await mountChips({ readings })
    const [shown, hidden] = chips()

    expect(shown!.text()).toBe('あに')
    expect(shown!.attributes('aria-pressed')).toBe('true')
    expect(shown!.classes()).not.toContain('line-through')
    expect(hidden!.text()).toBe('このかみ')
    expect(hidden!.attributes('aria-pressed')).toBe('false')
    expect(hidden!.classes()).toContain('line-through')
  })

  it('toggles a reading on click', async () => {
    const { chips, emitted } = await mountChips({ readings })

    await chips()[0]!.trigger('click')
    await chips()[1]!.trigger('click')

    expect(emitted()).toEqual([[1, false], [2, true]])
  })

  it('does not toggle while disabled', async () => {
    const { chips, emitted } = await mountChips({ readings, disabled: true })

    await chips()[0]!.trigger('click')

    expect(emitted()).toBeUndefined()
  })
})
