// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import CollectionMenuButton from '../../app/components/CollectionMenuButton.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

const collection = (id: number, name: string) => ({ id, name, description: null, created_at: '', updated_at: '' })
const verbos = collection(1, 'Verbos')
const n5 = collection(2, 'N5')
const cocina = collection(3, 'Cocina')

// The user has "Verbos" and "N5"; library entry 7 is in "N5". Creating
// "Cocina" answers with it.
function fakeBackend() {
  api.mockImplementation(async (url: string, options?: { method?: string }) => {
    if (url === '/collections/entries' && options?.method === 'POST') return cocina
    if (url === '/collections/entries') return [verbos, n5]
    if (url === '/library/entries/7/collections') return [n5]
    return undefined
  })
}

// UTooltip needs UApp; the menu is portalled to the body.
async function openMenu(props: Record<string, unknown>) {
  const wrapper = await mountSuspended(defineComponent({
    render: () => h(UApp, null, { default: () => h(CollectionMenuButton, { kind: 'entries', ...props }) }),
  }), { attachTo: document.body })
  await wrapper.find('button[aria-label="Añadir a una colección"]').trigger('click')
  await flushPromises()
  const option = (text: string) =>
    [...document.body.querySelectorAll<HTMLElement>('[role="option"]')].find(o => o.textContent?.includes(text))
  return {
    option,
    async pick(text: string) {
      option(text)!.click()
      await flushPromises()
    },
    async search(term: string) {
      const input = document.body.querySelector<HTMLInputElement>('input')!
      input.value = term
      input.dispatchEvent(new Event('input', { bubbles: true }))
      await flushPromises()
    },
    emitted: () => wrapper.findComponent(CollectionMenuButton).emitted('import'),
  }
}

enableAutoUnmount(afterEach)
beforeEach(() => {
  api.mockReset()
  document.body.innerHTML = ''
  fakeBackend()
})

describe('CollectionMenuButton', () => {
  it('ticks the collections an imported item is in', async () => {
    const menu = await openMenu({ practiceId: 7 })

    expect(menu.option('N5')!.getAttribute('aria-selected')).toBe('true')
    expect(menu.option('Verbos')!.getAttribute('aria-selected')).toBe('false')
  })

  it('asks to import an item that is not imported yet into the picked collection', async () => {
    const menu = await openMenu({})

    expect(api).not.toHaveBeenCalledWith('/library/entries/7/collections')
    await menu.pick('Verbos')

    expect(menu.emitted()).toEqual([[verbos]])
    expect(api).not.toHaveBeenCalledWith(expect.stringContaining('/items/'), expect.anything())
  })

  it('adds and removes an imported item', async () => {
    const menu = await openMenu({ practiceId: 7 })

    await menu.pick('Verbos')
    await menu.pick('N5')

    expect(api).toHaveBeenCalledWith('/collections/entries/1/items/7', { method: 'PUT' })
    expect(api).toHaveBeenCalledWith('/collections/entries/2/items/7', { method: 'DELETE' })
    expect(menu.emitted()).toBeUndefined()
  })

  it('creates a collection and imports the item into it', async () => {
    const menu = await openMenu({})

    await menu.search('Cocina')
    await menu.pick('Crear «Cocina»')

    expect(api).toHaveBeenCalledWith('/collections/entries', {
      method: 'POST',
      body: { name: 'Cocina', description: null },
    })
    expect(menu.emitted()).toEqual([[cocina]])
  })

  it('looks like the import button beside it', async () => {
    const wrapper = await mountSuspended(defineComponent({
      render: () => h(UApp, null, { default: () => [
        h(CollectionMenuButton, { kind: 'entries', practiceId: 7, iconOnly: true }),
        h(CollectionMenuButton, { kind: 'entries' }),
      ] }),
    }))
    const [imported, missing] = wrapper.findAll('button[aria-label="Añadir a una colección"]').map(b => b.classes())

    expect(imported).toEqual(expect.arrayContaining(['text-success', 'bg-success/10', 'p-1.5']))
    expect(imported).not.toContain('bg-elevated/50')
    expect(imported).not.toContain('ps-8')
    expect(missing).toEqual(expect.arrayContaining(['text-inverted', 'bg-primary']))
  })
})
