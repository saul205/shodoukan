// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { signedInAuth } from '../fakes'

const { api, navigate } = vi.hoisted(() => ({ api: vi.fn(), navigate: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
mockNuxtImport('navigateTo', () => navigate)
enableAutoUnmount(afterEach)
beforeEach(() => {
  api.mockReset()
  navigate.mockReset()
})

const noMatches = { entries: { items: [], total: 0, limit: 10, offset: 0 }, kanji: [] }

async function mountPage(route = '/library/entries/new') {
  const { default: NewEntryPage } = await import('../../app/pages/library/entries/new.vue')
  const wrapper = await mountSuspended(NewEntryPage, { route })
  await flushPromises()
  return wrapper
}

describe('new entry page', () => {
  it('creates a word of the user\'s own in the collection it was opened from', async () => {
    api.mockImplementation(async (url: string) => {
      if (url === '/collections/entries/4') return { id: 4, name: 'Contadores', description: null }
      if (url === '/library/entries/own') return { id: 12 }
      return noMatches
    })
    const wrapper = await mountPage('/library/entries/new?collection=4')

    expect(wrapper.text()).toContain('Contadores')
    await wrapper.find('input[data-testid="spellings"]').setValue('三匹')
    await wrapper.find('input[data-testid="readings"]').setValue('さんびき、サンビキ')
    await wrapper.find('input[data-testid="meaning"]').setValue(' three animals ')
    await wrapper.find('[data-testid="new-entry-form"]').trigger('submit')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/library/entries/own', {
      method: 'POST',
      body: {
        spellings: ['三匹'],
        readings: ['さんびき', 'サンビキ'],
        meaning: 'three animals',
        lang: 'eng',
        collection_ids: [4],
      },
    })
    expect(navigate).toHaveBeenCalledWith({ path: '/library/entries/12', query: { collection: 4 } })
  })

  it('needs readings in kana and a meaning', async () => {
    api.mockResolvedValue(noMatches)
    const wrapper = await mountPage()

    await wrapper.find('input[data-testid="readings"]').setValue('sanbiki')
    await wrapper.find('input[data-testid="meaning"]').setValue('three')
    await wrapper.find('[data-testid="new-entry-form"]').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('hiragana o katakana')
    expect(api).not.toHaveBeenCalledWith('/library/entries/own', expect.anything())
  })

  it('shows the dictionary\'s words written the same way', async () => {
    vi.useFakeTimers()
    api.mockResolvedValue({
      entries: {
        items: [{
          id: 1000001, kanji_readings: [{ kanji: '食べる' }], readings: [{ text: 'たべる' }],
          senses: [{ glosses: [{ text: 'to eat', lang: 'eng' }] }],
        }],
        total: 1, limit: 10, offset: 0,
      },
      kanji: [],
    })
    const wrapper = await mountPage()

    await wrapper.find('input[data-testid="spellings"]').setValue('食べる')
    await vi.advanceTimersByTimeAsync(500)
    vi.useRealTimers()
    await flushPromises()

    const alert = wrapper.find('[data-testid="dictionary-matches"]')
    expect(alert.text()).toContain('食べる · to eat')
    expect(api).toHaveBeenCalledWith('/dictionary/search', { query: { q: '食べる', lang: 'en', limit: 10, offset: 0 } })
  })
})
