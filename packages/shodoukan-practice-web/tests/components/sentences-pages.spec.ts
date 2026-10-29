// @vitest-environment nuxt
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import type { Morpheme, PracticeSentence, SentenceProposal } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
enableAutoUnmount(afterEach)

function mountPage(page: object, route: string) {
  return mountSuspended(defineComponent({ render: () => h(UApp, null, { default: () => h(page) }) }), { route })
}

function morphemes(...parts: [string, string][]): Morpheme[] {
  let at = 0
  return parts.map(([surface, lemma]) => {
    const m = { surface, lemma, reading: '', pos: [], start: at, end: at + surface.length }
    at += surface.length
    return m
  })
}

const ATE = '昨日パンを食べた。'
const BRIDGE = 'はしを渡る。'

const proposals: SentenceProposal[] = [
  {
    text: ATE,
    morphemes: morphemes(['昨日', '昨日'], ['パン', 'パン'], ['を', 'を'], ['食べ', '食べる'], ['た', 'た'], ['。', '。']),
    words: [{ start: 5, end: 8, form: '食べる', entry_ids: [7], certain: true }],
  },
  {
    text: BRIDGE,
    morphemes: morphemes(['はし', 'はし'], ['を', 'を'], ['渡る', '渡る'], ['。', '。']),
    words: [{ start: 0, end: 2, form: 'はし', entry_ids: [8, 9], certain: false }],
  },
]

describe('adding sentences in bulk', () => {
  it('reviews the analysis and stores only what is certain or confirmed', async () => {
    api.mockImplementation(async (url: string, options?: { method?: string; body?: unknown }) => {
      if (url === '/library/sentences/analyze') return proposals
      if (url === '/library/sentences/batch') return [{}, {}]
      if (url === '/library/entries') return { items: [], total: 0, limit: 20, offset: 0 }
      return {}
    })
    const { default: NewPage } = await import('../../app/pages/library/sentences/new.vue')
    const wrapper = await mountPage(NewPage, '/library/sentences/new')

    await wrapper.find('textarea').setValue(`${ATE}\tI ate bread.\n\n${BRIDGE}`)
    await wrapper.find('[data-testid="analyze"]').trigger('click')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/library/sentences/analyze', { method: 'POST', body: { texts: [ATE, BRIDGE] } })
    const rows = wrapper.findAll('[data-testid="review-row"]')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('1 enlazadas')
    expect(rows[0]!.text()).toContain('I ate bread.')
    expect(rows[1]!.text()).toContain('1 dudosas')

    await wrapper.find('[data-testid="save-all"]').trigger('click')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/library/sentences/batch', {
      method: 'POST',
      body: {
        sentences: [
          { japanese: ATE, translation: 'I ate bread.', lang: 'eng', words: [{ start: 5, end: 8, entry_id: 7 }] },
          // The kana-only match isn't confirmed: left out.
          { japanese: BRIDGE, translation: null, lang: 'eng', words: [] },
        ],
      },
    })
  })
})

describe('the sentence editor', () => {
  const sentence: PracticeSentence = {
    id: 4, text: ATE, translations: [{ lang: 'eng', text: 'I ate bread.' }],
    words: [{ id: 1, start: 5, end: 8, lemma: '食べる', reading: 'たべた', pos: ['動詞'], inflection: { endings: ['た'], form: '終止形' }, entry_id: 7, sense_id: null }],
    is_active: true, notes: null, origin: 'added', created_at: '', updated_at: '',
  }

  it('marks a word by clicking it and links a suggestion', async () => {
    const withBread = { ...sentence, words: [...sentence.words, { ...sentence.words[0]!, id: 2, start: 2, end: 4, entry_id: null }] }
    api.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === '/library/sentences/4' && !options) return sentence
      if (url === '/library/sentences/analyze') {
        return [{ ...proposals[0]!, words: [...proposals[0]!.words, { start: 0, end: 2, form: '昨日', entry_ids: [3], certain: true }] }]
      }
      if (url === '/library/sentences/4/words') return withBread
      if (url.startsWith('/library/entries')) return { items: [], total: 0, limit: 20, offset: 0 }
      return {}
    })
    const { default: EditorPage } = await import('../../app/pages/library/sentences/[id].vue')
    const wrapper = await mountPage(EditorPage, '/library/sentences/4')
    await flushPromises()

    expect(wrapper.find('[data-testid="sentence-text"]').text()).toBe(ATE)
    expect(wrapper.findAll('[data-testid="sentence-word"]')).toHaveLength(1)
    // 食べた is marked already; 昨日 is suggested.
    expect(wrapper.find('[data-testid="suggestions"]').text()).toContain('昨日')

    const bread = wrapper.findAll('[data-testid="morphemes"] button').find(b => b.text() === 'パン')!
    await bread.trigger('click')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/library/sentences/4/words', { method: 'POST', body: { start: 2, end: 4, entry_id: null } })
    expect(wrapper.findAll('[data-testid="sentence-word"]')).toHaveLength(2)

    const link = wrapper.find('[data-testid="suggestions"] button')
    await link.trigger('click')
    await flushPromises()
    expect(api).toHaveBeenCalledWith('/library/sentences/4/words', { method: 'POST', body: { start: 0, end: 2, entry_id: 3 } })
  })
})
