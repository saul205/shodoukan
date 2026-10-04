// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import ItemCollections from '../../app/components/ItemCollections.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

const collection = (id: number, name: string) => ({ id, name, description: null, created_at: '', updated_at: '' })
const verbos = collection(1, 'Verbos')
const n5 = collection(2, 'N5')
const cocina = collection(3, 'Cocina')

// Kanji 7 is in `mine`; creating "Cocina" answers with it.
function fakeBackend(all: unknown[], mine: unknown[]) {
  api.mockImplementation(async (url: string, options?: { method?: string }) => {
    if (url === '/collections/kanji' && options?.method === 'POST') return cocina
    if (url === '/collections/kanji') return all
    if (url === '/library/kanji/7/collections') return mine
    return undefined
  })
}

// UTooltip needs UApp; the menu's content is portalled to the body.
async function mountSection() {
  const wrapper = await mountSuspended(defineComponent({
    render: () => h(UApp, null, { default: () => h(ItemCollections, { kind: 'kanji', itemId: 7 }) }),
  }), { attachTo: document.body })
  await flushPromises()
  return wrapper
}

async function createFromHeader(wrapper: Awaited<ReturnType<typeof mountSection>>, name: string) {
  await wrapper.find('button[aria-label="Añadir a una colección"]').trigger('click')
  await flushPromises()
  const input = document.body.querySelector<HTMLInputElement>('input')!
  input.value = name
  input.dispatchEvent(new Event('input', { bubbles: true }))
  await flushPromises()
  const create = [...document.body.querySelectorAll<HTMLElement>('[role="option"]')].find(o => o.textContent?.includes(`Crear «${name}»`))
  create!.click()
  await flushPromises()
}

enableAutoUnmount(afterEach)
beforeEach(() => {
  api.mockReset()
  document.body.innerHTML = ''
})

describe('ItemCollections', () => {
  it('lists the collections the item is in', async () => {
    fakeBackend([verbos, n5], [n5])
    const wrapper = await mountSection()

    expect(wrapper.find('a[href="/collections/kanji/2"]').text()).toBe('N5')
    expect(wrapper.text()).not.toContain('Verbos')
  })

  it('adds the item to a collection picked from the header icon', async () => {
    fakeBackend([verbos, n5], [n5])
    const wrapper = await mountSection()

    await wrapper.find('button[aria-label="Añadir a una colección"]').trigger('click')
    await flushPromises()
    const option = [...document.body.querySelectorAll('[role="option"]')].find(o => o.textContent?.includes('Verbos'))
    expect(option).toBeDefined()
    ;(option as HTMLElement).click()
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/collections/kanji/1/items/7', { method: 'PUT' })
  })

  it('creates a collection and adds the item even when it is in every other one', async () => {
    fakeBackend([n5], [n5])
    const wrapper = await mountSection()

    await createFromHeader(wrapper, 'Cocina')

    expect(api).toHaveBeenCalledWith('/collections/kanji', { method: 'POST', body: { name: 'Cocina', description: null } })
    expect(api).toHaveBeenCalledWith('/collections/kanji/3/items/7', { method: 'PUT' })
  })

  it('lets the user create the first collection', async () => {
    fakeBackend([], [])
    const wrapper = await mountSection()

    expect(wrapper.text()).toContain('Aún no tienes colecciones.')
    await createFromHeader(wrapper, 'Cocina')

    expect(api).toHaveBeenCalledWith('/collections/kanji/3/items/7', { method: 'PUT' })
  })
})
