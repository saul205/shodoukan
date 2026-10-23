// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { USelect, USelectMenu } from '#components'
import DirectionsEditor from '../../app/components/DirectionsEditor.vue'
import type { Direction } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

async function mountEditor(kind: 'entries' | 'kanji', directions: Direction[]) {
  // Feed updates back like a parent's v-model would.
  const wrapper = await mountSuspended(DirectionsEditor, {
    props: {
      kind,
      'modelValue': directions,
      'onUpdate:modelValue': (value: Direction[]) => wrapper.setProps({ modelValue: value }),
    },
  })
  const updates = () => wrapper.emitted('update:modelValue') as [Direction[]][] | undefined
  return { wrapper, updates }
}

describe('DirectionsEditor', () => {
  it('never offers the asked field among the shown ones', async () => {
    const { wrapper } = await mountEditor('kanji', [{ prompt: ['literal'], answer: 'kunyomi' }])

    const offered = wrapper.findComponent(USelectMenu).props('items') as { value: string }[]
    expect(offered.map(item => item.value)).toEqual(['literal', 'onyomi', 'meaning'])
  })

  it('takes a field out of the prompt when it becomes the answer', async () => {
    const { wrapper, updates } = await mountEditor('entries', [{ prompt: ['writing', 'reading'], answer: 'meaning' }])

    wrapper.findComponent(USelect).vm.$emit('update:modelValue', 'reading')

    expect(updates()?.at(-1)).toEqual([[{ prompt: ['writing'], answer: 'reading' }]])
  })

  it('adds a direction asking a field not asked yet, and removes one', async () => {
    const { wrapper, updates } = await mountEditor('entries', [{ prompt: ['writing'], answer: 'meaning' }])

    await wrapper.find('[data-testid="add-direction"]').trigger('click')
    expect(updates()?.at(-1)).toEqual([[
      { prompt: ['writing'], answer: 'meaning' },
      { prompt: ['reading'], answer: 'writing' },
    ]])

    await wrapper.find('[data-testid="remove-direction"]').trigger('click')
    expect(updates()?.at(-1)).toEqual([[{ prompt: ['reading'], answer: 'writing' }]])
  })
})
