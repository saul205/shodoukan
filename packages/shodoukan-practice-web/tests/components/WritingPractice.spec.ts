// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import { FetchError } from 'ofetch'
import WordWritingBoard from '../../app/components/WordWritingBoard.vue'
import WritingPractice from '../../app/components/WritingPractice.vue'
import type { PracticeItem } from '../../app/utils/writing-practice'
import { signedInAuth } from '../fakes'
import { stubResizeObserver } from '../resize-observer'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
enableAutoUnmount(afterEach)

const ICHI = [{ path: 'M14,54c20,0,60,0,80,0', label: null }]
const notFound = () => Object.assign(new FetchError('404 Not Found'), { statusCode: 404 })
const reading = (id: number, text: string, enabled = true) => ({ id, text, enabled })

const KANJI = {
  id: 7, literal: '日', on_readings: [reading(1, 'ニチ')], kun_readings: [reading(2, 'ひ'), reading(3, 'か', false)],
  meanings: [
    { id: 1, text: 'day', lang: 'en', enabled: true, origin: 'imported' },
    { id: 2, text: 'sun', lang: 'en', enabled: false, origin: 'imported' },
    { id: 3, text: 'día', lang: 'es', enabled: true, origin: 'imported' },
  ],
}
const ENTRY = {
  id: 9,
  kanji_readings: [{ id: 1, kanji: '食べる', info: [], enabled: true }],
  readings: [{ id: 1, text: 'たべる', no_kanji: false, info: [], restricted_to: [], enabled: true }],
  senses: [{ id: 1, glosses: [{ id: 1, text: 'to eat', lang: 'eng', enabled: true }] }],
}

beforeEach(() => {
  clearNuxtData()
  stubResizeObserver({ width: 900, height: 300 })
  api.mockReset()
  api.mockImplementation(async (url: string) => {
    if (url === '/library/kanji/7') return KANJI
    if (url === '/library/entries/9') return ENTRY
    if (url.startsWith('/library/')) throw notFound()
    if (url.endsWith('/strokes')) {
      if (url.includes(encodeURIComponent('〆'))) throw notFound()
      return { literal: '?', strokes: ICHI }
    }
    if (url.startsWith('/dictionary/kanji/')) return { meanings: [{ text: 'one', lang: 'en' }] }
    throw new Error(`unexpected ${url}`)
  })
})
afterEach(() => vi.unstubAllGlobals())

async function practice(items: PracticeItem[], mode = 'guided-free', repetitions = 1) {
  const wrapper = await mountSuspended(WritingPractice, { props: { items, mode, repetitions } })
  await flushPromises()
  return wrapper
}

const chars = (...texts: string[]): PracticeItem[] => texts.map(text => ({ kind: 'char', text }))
const text = (wrapper: Awaited<ReturnType<typeof practice>>, id: string) => wrapper.get(`[data-testid="${id}"]`).text()

async function finishItem(wrapper: Awaited<ReturnType<typeof practice>>) {
  wrapper.findComponent(WordWritingBoard).vm.$emit('done')
  await wrapper.vm.$nextTick()
  await wrapper.get('[data-testid="practice-next"]').trigger('click')
  await flushPromises()
}

describe('WritingPractice', () => {
  it('guides an item once, then lets it be written freely, then goes on', async () => {
    const wrapper = await practice(chars('一', '二'))
    expect(text(wrapper, 'practice-text')).toBe('一')
    expect(text(wrapper, 'practice-step')).toBe('Guiado')
    expect(text(wrapper, 'practice-progress')).toBe('1 / 2')
    expect(wrapper.findComponent(WordWritingBoard).props('guided')).toBe(true)
    expect(wrapper.find('[data-testid="practice-next-row"]').exists()).toBe(false)

    await finishItem(wrapper)
    expect(wrapper.findComponent(WordWritingBoard).props('guided')).toBe(false)
    expect(text(wrapper, 'practice-step')).toBe('Libre · 1 de 1')

    await finishItem(wrapper)
    expect(text(wrapper, 'practice-text')).toBe('二')

    await finishItem(wrapper)
    await finishItem(wrapper)
    expect(wrapper.emitted('finished')).toHaveLength(1)
  })

  it('writes a word whole, with the reading and meanings of the library', async () => {
    const wrapper = await practice([{ kind: 'entry', id: 9 }], 'free')

    expect(text(wrapper, 'practice-text')).toBe('食べる')
    expect(text(wrapper, 'practice-reading')).toBe('たべる')
    expect(text(wrapper, 'practice-meanings')).toBe('to eat')
    expect(wrapper.findComponent(WordWritingBoard).props('chars')).toEqual(['食', 'べ', 'る'])
  })

  it("shows a library kanji's own readings and meanings, only the enabled ones", async () => {
    const wrapper = await practice([{ kind: 'kanji', id: 7 }], 'free')

    expect(text(wrapper, 'practice-text')).toBe('日')
    expect(text(wrapper, 'practice-reading')).toBe('ひ・ニチ')
    expect(text(wrapper, 'practice-meanings')).toBe('day')
  })

  it("shows a bare kanji's dictionary meanings", async () => {
    const wrapper = await practice(chars('一'), 'free')

    expect(text(wrapper, 'practice-meanings')).toBe('one')
  })

  it('starts an item over with Otra vez', async () => {
    const wrapper = await practice(chars('一'), 'free')
    const first = wrapper.findComponent(WordWritingBoard).vm
    first.$emit('done')
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-testid="practice-again"]').trigger('click')

    expect(wrapper.findComponent(WordWritingBoard).vm).not.toBe(first)
    expect(wrapper.find('[data-testid="practice-next-row"]').exists()).toBe(false)
  })

  it('passes over a lone character without a drawing, and an item gone from the library', async () => {
    const wrapper = await practice([...chars('〆'), { kind: 'kanji', id: 99 }, ...chars('一')], 'guided-free', 2)
    expect(wrapper.find('[data-testid="practice-missing"]').exists()).toBe(true)

    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    await flushPromises()
    expect(text(wrapper, 'practice-missing')).toContain('Ya no está en tu librería')

    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    await flushPromises()
    expect(text(wrapper, 'practice-text')).toBe('一')
    expect(text(wrapper, 'practice-step')).toBe('Guiado')
  })

  it('restarts the same item when the mode changes', async () => {
    const wrapper = await practice(chars('一', '二', '三'), 'guided-free', 2)
    // 一 guided, then twice free: on to 二, guided (the fourth step).
    for (let i = 0; i < 3; i++) await finishItem(wrapper)
    expect(text(wrapper, 'practice-text')).toBe('二')

    await wrapper.setProps({ mode: 'guided' })
    await flushPromises()

    expect(text(wrapper, 'practice-text')).toBe('二')
    expect(text(wrapper, 'practice-step')).toBe('Guiado')
  })

  it("doesn't show the previous item while the next one loads", async () => {
    const wrapper = await practice(chars('一', '二'), 'free')
    const pending: ((value: unknown) => void)[] = []
    const answer = api.getMockImplementation()!
    api.mockImplementation((url: string) => new Promise(r => pending.push(() => r(answer(url)))))
    wrapper.findComponent(WordWritingBoard).vm.$emit('done')
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(wrapper.get('[data-testid="practice-text"]').text()).not.toBe('一')
    expect(wrapper.findComponent(WordWritingBoard).exists()).toBe(false)

    // The item, then its strokes.
    while (pending.length) {
      pending.splice(0).forEach(resolve => resolve(undefined))
      await flushPromises()
    }
    expect(text(wrapper, 'practice-text')).toBe('二')
    expect(wrapper.findComponent(WordWritingBoard).props('chars')).toEqual(['二'])
  })

  it('shows a library item as it is when a later practice starts, edited or removed', async () => {
    const first = await practice([{ kind: 'entry', id: 9 }], 'free')
    expect(text(first, 'practice-text')).toBe('食べる')
    first.unmount()

    // The first spelling is hidden in the library meanwhile: the next one is written.
    const edited = {
      ...ENTRY,
      kanji_readings: [
        { ...ENTRY.kanji_readings[0]!, enabled: false },
        { id: 2, kanji: '喰べる', info: [], enabled: true },
      ],
      senses: [{ id: 1, glosses: [{ id: 1, text: 'to devour', lang: 'eng', enabled: true }] }],
    }
    const answer = api.getMockImplementation()!
    api.mockImplementation(async (url: string) => (url === '/library/entries/9' ? edited : answer(url)))
    const second = await practice([{ kind: 'entry', id: 9 }], 'free')
    expect(text(second, 'practice-text')).toBe('喰べる')
    expect(text(second, 'practice-meanings')).toBe('to devour')
    second.unmount()

    api.mockImplementation(async (url: string) => {
      if (url === '/library/entries/9') throw notFound()
      return answer(url)
    })
    const third = await practice([{ kind: 'entry', id: 9 }], 'free')
    expect(text(third, 'practice-missing')).toContain('Ya no está en tu librería')
  })
})
