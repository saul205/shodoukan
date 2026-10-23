// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import CollectionPicker from '../../app/components/CollectionPicker.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

const collection = (id: number, name: string) => ({ id, name, description: null, created_at: '', updated_at: '' })
const verbos = collection(1, 'Verbos')
const n5 = collection(2, 'N5')

// UTooltip needs UApp; the menu is portalled to the body.
async function openPicker(props: Record<string, unknown>) {
  const wrapper = await mountSuspended(defineComponent({
    render: () => h(UApp, null, { default: () => h(CollectionPicker, props) }),
  }), { attachTo: document.body })
  await wrapper.find('button[aria-label="Añadir a una colección"]').trigger('click')
  await flushPromises()
  const options = () => [...document.body.querySelectorAll<HTMLElement>('[role="option"]')]
  return {
    options,
    option: (text: string) => options().find(o => o.textContent?.includes(text)),
    async search(term: string) {
      const input = document.body.querySelector<HTMLInputElement>('input')!
      input.value = term
      input.dispatchEvent(new Event('input', { bubbles: true }))
      await flushPromises()
    },
    emitted: (event: string) => wrapper.findComponent(CollectionPicker).emitted(event),
  }
}

// Unmount before clearing the body, or the open menu's portal outlives it.
enableAutoUnmount(afterEach)
beforeEach(() => {
  document.body.innerHTML = ''
})

describe('CollectionPicker', () => {
  it('offers only the other collections in library mode, and adds the picked one', async () => {
    const picker = await openPicker({ collections: [verbos, n5], selected: [n5] })

    expect(picker.options().map(o => o.textContent?.trim())).toEqual(['Verbos'])
    picker.option('Verbos')!.click()
    await flushPromises()

    expect(picker.emitted('add')).toEqual([[verbos]])
  })

  it('ticks the selected ones in dictionary mode and emits what changes', async () => {
    const picker = await openPicker({ collections: [verbos, n5], selected: [n5], showSelected: true })

    expect(picker.option('N5')!.getAttribute('aria-selected')).toBe('true')
    expect(picker.option('Verbos')!.getAttribute('aria-selected')).toBe('false')
    picker.option('N5')!.click()
    await flushPromises()
    picker.option('Verbos')!.click()
    await flushPromises()

    expect(picker.emitted('remove')).toEqual([[n5]])
    expect(picker.emitted('add')).toEqual([[verbos]])
  })

  it('offers to create a collection with the name being searched', async () => {
    const picker = await openPicker({ collections: [verbos], selected: [] })

    await picker.search('Cocina')
    picker.option('Crear «Cocina»')!.click()
    await flushPromises()

    expect(picker.emitted('create')).toEqual([['Cocina']])
  })
})
