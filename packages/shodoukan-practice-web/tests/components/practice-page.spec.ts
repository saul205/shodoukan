// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import PracticePage from '../../app/pages/practice/index.vue'
import { signedInAuth } from '../fakes'

const { api, navigate } = vi.hoisted(() => ({ api: vi.fn(), navigate: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
mockNuxtImport('navigateTo', () => navigate)
enableAutoUnmount(afterEach)

const kanji = (id: number, literal: string) => ({ id, literal })

beforeEach(() => {
  clearNuxtData()
  navigate.mockReset()
  api.mockReset()
  api.mockImplementation(async (url: string, options?: { query?: { offset?: number } }) => {
    if (url === '/collections/kanji') return [{ id: 3, name: 'Kanji N5', description: null, created_at: '', updated_at: '' }]
    if (url === '/collections/kanji/3/items') {
      // Two pages of the API's largest size, and one more.
      const offset = options?.query?.offset ?? 0
      const items = offset === 0 ? [kanji(1, '日'), kanji(2, '本')] : offset === 100 ? [kanji(3, '人')] : []
      return { items, total: 3, limit: 100, offset }
    }
    if (url === '/library/kanji') return { items: [], total: 0, limit: 100, offset: 0 }
    throw new Error(`unexpected ${url}`)
  })
})

describe('practice page', () => {
  it('practises every active kanji of the preselected collection', async () => {
    const wrapper = await mountSuspended(PracticePage, { route: '/practice?collection=3' })
    await flushPromises()

    await wrapper.get('[data-testid="practice-start"]').trigger('click')
    await flushPromises()

    const itemCalls = api.mock.calls.filter(([url]) => url === '/collections/kanji/3/items')
    expect(itemCalls.map(([, options]) => options.query)).toEqual([
      { limit: 100, offset: 0, active: true },
      { limit: 100, offset: 100, active: true },
    ])
    const [[target]] = navigate.mock.calls
    expect(target.path).toBe('/practice/play')
    expect([...target.query.chars].sort()).toEqual(['人', '日', '本'].sort())
    expect(target.query).toMatchObject({ mode: 'guided-free', reps: 2 })
  })

  it("can't start without a collection, and says when there is nothing to practise", async () => {
    const wrapper = await mountSuspended(PracticePage, { route: '/practice' })
    await flushPromises()
    expect(wrapper.get('[data-testid="practice-start"]').attributes('disabled')).toBeDefined()

    const library = wrapper.findAll('[data-testid="practice-source"] [role="radio"]').find(r => r.attributes('value') === 'library')!
    await library.trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="practice-start"]').trigger('click')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/library/kanji', { query: { limit: 100, offset: 0, active: true } })
    expect(navigate).not.toHaveBeenCalled()
  })
})
