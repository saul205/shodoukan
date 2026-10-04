// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import KanjiWords from '../../app/components/KanjiWords.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

function word(id: number, kanji: string, reading: string, gloss: string) {
  return {
    id,
    kanji_readings: [{ kanji, info: [] }],
    readings: [{ text: reading, no_kanji: false, info: [], restricted_to: [] }],
    senses: [{ pos: [], misc: [], dialects: [], info: [], cross_references: [], examples: [], glosses: [{ text: gloss, type: null, lang: 'eng' }] }],
    jlpt: null,
    is_common: true,
  }
}

const taberu = word(1, '食べる', 'たべる', 'to eat')
const inshoku = word(2, '飲食', 'いんしょく', 'food and drink')

// The dictionary has `total` words with 食; the user imported 食べる as entry 70.
function fakeBackend(items: unknown[], total: number) {
  api.mockImplementation(async (url: string) => {
    if (url === `/dictionary/kanji/${encodeURIComponent('食')}/entries`) return { items, total, limit: 5, offset: 0 }
    if (url === '/library/imported') return { entries: [{ source_entry_id: 1, id: 70 }], kanji: [] }
    return undefined
  })
}

async function mountWords() {
  const wrapper = await mountSuspended(KanjiWords, { props: { literal: '食' } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  api.mockReset()
  clearNuxtData() // the words are cached by kanji, as in the app
})

describe('KanjiWords', () => {
  it('opens imported words in the library and the rest in the dictionary', async () => {
    fakeBackend([taberu, inshoku], 2)
    const wrapper = await mountWords()

    const links = wrapper.findAll('li a').map(a => [a.text(), a.attributes('href')])
    expect(links).toEqual([
      [expect.stringContaining('食べる'), '/library/entries/70'],
      [expect.stringContaining('飲食'), '/dictionary/entries/2'],
    ])
    expect(wrapper.text()).toContain('to eat')
    expect(wrapper.text()).not.toContain('Ver las')
  })

  it('links to every word on the dictionary page when there are more', async () => {
    fakeBackend([taberu, inshoku], 42)
    const wrapper = await mountWords()

    const more = wrapper.findAll('a').find(a => a.text().includes('Ver las 42 palabras'))
    expect(more?.attributes('href')).toBe(`/dictionary/kanji/食`)
  })

  it('shows nothing when no word uses the kanji', async () => {
    fakeBackend([], 0)
    const wrapper = await mountWords()

    expect(wrapper.find('section').exists()).toBe(false)
  })
})
