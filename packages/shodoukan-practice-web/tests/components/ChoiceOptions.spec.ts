// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import ChoiceOptions from '../../app/components/ChoiceOptions.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

const options = [
  { text: 'た.べる', item_id: 10 },
  { text: 'みず', item_id: 11 },
  { text: 'ひ', item_id: null },
]

describe('ChoiceOptions', () => {
  it('emits the picked option while unanswered', async () => {
    const wrapper = await mountSuspended(ChoiceOptions, { props: { options, picked: null, correct: null } })

    await wrapper.findAll('[data-testid="option"]')[1]!.trigger('click')

    expect(wrapper.emitted('pick')).toEqual([[1]])
    expect(wrapper.find('[data-testid="open-option-item"]').exists()).toBe(false)
  })

  it('marks the right option green and a wrong pick red once answered', async () => {
    const wrapper = await mountSuspended(ChoiceOptions, { props: { options, picked: 1, correct: 0 } })

    const buttons = wrapper.findAll('[data-testid="option"]')
    expect(buttons.map(b => b.attributes('data-state'))).toEqual(['correct', 'wrong', 'other'])
    await buttons[2]!.trigger('click')
    expect(wrapper.emitted('pick')).toBeUndefined()
  })

  it('opens the detail of the options that came from an item', async () => {
    const wrapper = await mountSuspended(ChoiceOptions, { props: { options, picked: 0, correct: 0 } })

    const details = wrapper.findAll('[data-testid="open-option-item"]')
    expect(details).toHaveLength(2)
    await details[1]!.trigger('click')
    expect(wrapper.emitted('open-item')).toEqual([[11]])
  })

  it('uses one column on phones for long options', async () => {
    const long = ['to eat something', 'water (cold, fresh)', 'sun; sunshine; day'].map(text => ({ text, item_id: null }))
    const wrapper = await mountSuspended(ChoiceOptions, { props: { options: long, picked: null, correct: null } })

    expect(wrapper.find('[data-testid="options"]').classes()).toContain('grid-cols-1')
  })

  it('uses two columns on phones for short options', async () => {
    const wrapper = await mountSuspended(ChoiceOptions, { props: { options, picked: null, correct: null, japanese: true } })

    const classes = wrapper.find('[data-testid="options"]').classes()
    expect(classes).toContain('grid-cols-2')
    expect(classes).not.toContain('grid-cols-1')
  })

  it('uses two columns on phones with 7 or 8 options', async () => {
    const eight = Array.from({ length: 8 }, (_, i) => ({ text: `o${i}`, item_id: null }))
    const wrapper = await mountSuspended(ChoiceOptions, { props: { options: eight, picked: null, correct: null } })

    const classes = wrapper.find('[data-testid="options"]').classes()
    expect(classes).toContain('grid-cols-2')
    expect(classes).not.toContain('grid-cols-1')
  })
})
