// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import LibrarySearchInput from '../../app/components/LibrarySearchInput.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

async function mountInput(modelValue = '') {
  const wrapper = await mountSuspended(LibrarySearchInput, { props: { modelValue } })
  const updates = () => wrapper.emitted('update:modelValue') as string[][] | undefined
  return { wrapper, input: () => wrapper.find('input'), updates }
}

describe('LibrarySearchInput', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('updates the model once typing pauses, trimmed', async () => {
    const { input, updates } = await mountInput()

    await input().setValue('ta')
    await input().setValue('taberu ')
    vi.advanceTimersByTime(299)
    expect(updates()).toBeUndefined()

    vi.advanceTimersByTime(1)
    expect(updates()).toEqual([['taberu']])
  })

  it('updates at once on Enter', async () => {
    const { input, updates } = await mountInput()

    await input().setValue('eat')
    await input().trigger('keydown', { key: 'Enter' })

    expect(updates()).toEqual([['eat']])
  })

  it('clears with the x button', async () => {
    const { wrapper, updates } = await mountInput('taberu')

    await wrapper.find('button[aria-label="Borrar la búsqueda"]').trigger('click')

    expect(updates()).toEqual([['']])
    expect(wrapper.find('input').element.value).toBe('')
  })

  it('follows the model when it changes from outside', async () => {
    const { wrapper, input } = await mountInput('taberu')

    await wrapper.setProps({ modelValue: 'mizu' })

    expect(input().element.value).toBe('mizu')
  })
})
