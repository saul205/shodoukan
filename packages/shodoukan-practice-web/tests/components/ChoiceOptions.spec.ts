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
})
