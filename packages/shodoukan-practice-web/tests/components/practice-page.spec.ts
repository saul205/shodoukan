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

/** A UCheckbox's box: the test id lands on its root or on the box itself. */
function checkbox(wrapper: Awaited<ReturnType<typeof mountSuspended>>, testId: string) {
  const element = wrapper.get(`[data-testid="${testId}"]`)
  return element.attributes('role') === 'checkbox' ? element : element.get('[role="checkbox"]')
}

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
    if (url === '/collections/entries') return [{ id: 4, name: 'Verbos', description: null, created_at: '', updated_at: '' }]
    if (url === '/collections/entries/4/items') {
      const word = (id: number, kanji: string | null, reading: string) => ({
        id, kanji_readings: kanji ? [{ id, kanji, info: [], enabled: true }] : [],
        readings: [{ id, text: reading, no_kanji: false, info: [], restricted_to: [], enabled: true }],
      })
      return { items: [word(1, '食べる', 'たべる'), word(2, null, 'これ')], total: 2, limit: 100, offset: 0 }
    }
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

  it("practises a word collection's words, with their readings", async () => {
    const wrapper = await mountSuspended(PracticePage, { route: '/practice?kind=entries&collection=4' })
    await flushPromises()
    await checkbox(wrapper, 'practice-shuffle').trigger('click') // in order

    await wrapper.get('[data-testid="practice-start"]').trigger('click')
    await flushPromises()

    expect(navigate.mock.calls[0]![0].query).toMatchObject({ words: '食べる:たべる,これ', mode: 'guided-free' })
  })

  it('practises the chosen kana rows, without the library', async () => {
    const wrapper = await mountSuspended(PracticePage, { route: '/practice' })
    await flushPromises()
    const tab = wrapper.findAll('[data-testid="practice-what"] [role="tab"]').find(t => t.text().includes('Kana'))!
    await tab.trigger('mousedown', { button: 0 })
    await tab.trigger('click')
    await flushPromises()

    await checkbox(wrapper, 'kana-row-hiragana-ka').trigger('click')
    await wrapper.get('[data-testid="kana-all-katakana"]').trigger('click')
    await wrapper.get('[data-testid="kana-all-katakana"]').trigger('click')
    await wrapper.get('[data-testid="practice-start"]').trigger('click')
    await flushPromises()

    expect([...navigate.mock.calls[0]![0].query.chars].sort()).toEqual([...'かきくけこ'].sort())
  })
})
