// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import { defineComponent, h } from 'vue'
import { UApp } from '#components'
import ListPage from '../../app/pages/public-collections/index.vue'
import DetailPage from '../../app/pages/public-collections/[kind]/[id].vue'
import { signedInAuth } from '../fakes'

const { api, toast } = vi.hoisted(() => ({ api: vi.fn(), toast: { add: vi.fn() } }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
mockNuxtImport('useToast', () => () => toast)
enableAutoUnmount(afterEach)

const n5 = {
  id: 7, name: 'JLPT N5', description: 'Básicas', owner: 'tanaka', is_mine: false, version: 2,
  published_at: '2026-10-13T10:00:00Z', item_count: 1, downloads: 3, imported_version: null,
}
const word = {
  id: 1, source_entry_id: 1000001, kanji_readings: [{ id: 2, kanji: '食べる', info: [], enabled: true, origin: 'imported' }],
  readings: [{ id: 3, text: 'たべる', no_kanji: false, info: [], restricted_to: [], enabled: true, origin: 'imported' }],
  senses: [{
    id: 4, pos: [], misc: [], dialects: [], info: [], notes: null, enabled: true, origin: 'imported',
    glosses: [
      { id: 5, text: 'to eat', lang: 'eng', type: null, enabled: true, origin: 'imported' },
      { id: 6, text: 'to scoff', lang: 'eng', type: null, enabled: true, origin: 'added' },
    ],
    examples: [],
  }],
  jlpt: 5, is_common: true, is_active: true, notes: 'Mi truco',
}

beforeEach(() => {
  clearNuxtData()
  toast.add.mockReset()
  api.mockReset()
  api.mockImplementation(async (url: string) => {
    if (url === '/public-collections/entries') return { items: [n5], total: 1, limit: 24, offset: 0 }
    if (url === '/public-collections/entries/7') return n5
    if (url === '/public-collections/entries/7/items') return { items: [word], total: 1, limit: 24, offset: 0 }
    if (url === '/library/imported') return { entries: [{ source_entry_id: 1000001, id: 99 }], kanji: [] }
    if (url === '/public-collections/entries/7/import') {
      return { collection: { id: 30, name: 'JLPT N5' }, created: 1, existing: 0, missing: [] }
    }
    throw new Error(`unexpected ${url}`)
  })
})

describe('public collections', () => {
  it('lists them with their owner and counts, searching from the URL', async () => {
    const wrapper = await mountSuspended(ListPage, { route: '/public-collections?q=n5&owner=others' })
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/public-collections/entries', {
      query: { q: 'n5', owner: 'others', sort: 'popular', limit: 24, offset: 0 },
    })
    const card = wrapper.get('[data-testid="public-collection"]')
    expect(card.attributes('href')).toBe('/public-collections/entries/7')
    expect(card.text()).toContain('de tanaka')
    expect(card.text()).toContain('3 descargas')
  })

  it('previews one and imports it', async () => {
    const wrapper = await mountSuspended(DetailPage, { route: '/public-collections/entries/7' })
    await flushPromises()

    expect(wrapper.text()).toContain('食べる')
    expect(wrapper.find('a[href^="/library"]').exists()).toBe(false)
    expect(api).toHaveBeenCalledWith('/library/imported', { query: { entry_ids: [1000001], literals: [] } })
    expect(wrapper.get('[data-testid="preview-item"]').text()).toContain('En tu librería')
    await wrapper.get('[data-testid="import-public"]').trigger('click')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/public-collections/entries/7/import', { method: 'POST' })
    expect(toast.add).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Importada como «JLPT N5»',
      description: '1 nuevo, 0 ya estaban en tu librería',
    }))
  })
})

describe('a public collection item', () => {
  it('opens view-only, marking what the owner added and their note', async () => {
    // The modal is an overlay: it needs the UApp the real app has.
    const wrapper = await mountSuspended(
      defineComponent({ render: () => h(UApp, null, { default: () => h(DetailPage) }) }),
      { route: '/public-collections/entries/7', attachTo: document.body },
    )
    await flushPromises()

    await wrapper.get('[data-testid="preview-item"]').trigger('click')
    await flushPromises()

    const modal = document.body.textContent ?? ''
    expect(modal).toContain('to scoff')
    expect(modal).toContain('de tanaka')
    expect(modal).toContain('Nota de tanaka')
    expect(modal).toContain('Mi truco')
    expect(modal).not.toContain('propio')
  })
})
