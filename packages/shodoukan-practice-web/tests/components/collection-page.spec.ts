// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import CollectionPage from '../../app/pages/collections/[kind]/[id].vue'
import { signedInAuth } from '../fakes'

const { api, toast } = vi.hoisted(() => ({ api: vi.fn(), toast: { add: vi.fn() } }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
mockNuxtImport('useToast', () => () => toast)
enableAutoUnmount(afterEach)

const copy = {
  id: 3, name: 'JLPT N5', description: null, is_public: false, published_version: 0, published_at: null,
  source_collection_id: 9, source_version: 1, latest_source_version: 2, created_at: '', updated_at: '',
}

beforeEach(() => {
  clearNuxtData()
  toast.add.mockReset()
  api.mockReset()
  api.mockImplementation(async (url: string) => {
    if (url === '/collections/entries/3') return copy
    if (url === '/collections/entries/3/items') return { items: [], total: 0, limit: 24, offset: 0 }
    if (url === '/collections/entries/3/update') {
      return { collection: { ...copy, source_version: 2 }, created: 1, existing: 2, missing: [], removed: 1 }
    }
    throw new Error(`unexpected ${url}`)
  })
})

describe('a copy of a public collection', () => {
  it('offers its source\'s new version and applies it', async () => {
    const wrapper = await mountSuspended(CollectionPage, { route: '/collections/entries/3' })
    await flushPromises()

    const notice = wrapper.get('[data-testid="source-update"]')
    expect(notice.text()).toContain('Hay una versión nueva (2)')
    await notice.get('button').trigger('click')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/collections/entries/3/update', { method: 'POST' })
    expect(toast.add).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Actualizada a la versión 2',
      description: '1 nuevo, 2 revisados, 1 quitado de la colección',
    }))
  })

  it('says nothing when it follows the latest version', async () => {
    api.mockImplementation(async (url: string) => {
      if (url === '/collections/entries/3') return { ...copy, source_version: 2 }
      return { items: [], total: 0, limit: 24, offset: 0 }
    })
    const wrapper = await mountSuspended(CollectionPage, { route: '/collections/entries/3' })
    await flushPromises()

    expect(wrapper.find('[data-testid="source-update"]').exists()).toBe(false)
  })
})
