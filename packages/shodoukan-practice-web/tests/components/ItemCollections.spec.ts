// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'
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

// Kanji 7 is in "N5"; the user also has "Verbos".
function fakeBackend(all: unknown[], mine: unknown[]) {
  api.mockImplementation(async (url: string) => {
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

  it('disables the icon when the item is in every collection', async () => {
    fakeBackend([n5], [n5])
    const wrapper = await mountSection()

    const icon = wrapper.find('button[aria-label="Ya está en todas tus colecciones"]')
    expect(icon.attributes('disabled')).toBeDefined()
  })

  it('offers to create one when there are none', async () => {
    fakeBackend([], [])
    const wrapper = await mountSection()

    expect(wrapper.text()).toContain('Aún no tienes colecciones.')
    expect(wrapper.find('button[aria-label="Añadir a una colección"]').exists()).toBe(false)
  })
})
