// @vitest-environment nuxt
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import type { PracticeEntry } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
enableAutoUnmount(afterEach)

function word(sourceId: number | null, readingEnabled = true): PracticeEntry {
  return {
    id: 7, source_entry_id: sourceId, jlpt: null, is_common: false, is_active: true, notes: null,
    created_at: '', updated_at: '',
    kanji_readings: [{ id: 1, kanji: '三匹', info: [], enabled: true, origin: 'added' }],
    readings: [{ id: 2, text: 'さんびき', no_kanji: false, info: [], restricted_to: [], enabled: readingEnabled, origin: 'added' }],
    senses: [],
  }
}

function kanji(literal: string) {
  return { literal, grade: null, stroke_count: 3, freq: null, jlpt: null, on_readings: [], kun_readings: [], nanori: [], meanings: [] }
}

describe('library entry page', () => {
  it('doesn\'t fetch the word\'s kanji again after an edit', async () => {
    api.mockImplementation(async (url: string, options?: { method?: string }) => {
      if (url === '/library/entries/7') return word(null)
      if (url === '/library/entries/7/readings/2/enabled' && options?.method === 'PUT') return word(null, false)
      if (url.startsWith('/dictionary/kanji/')) return kanji(decodeURIComponent(url.split('/').pop()!))
      if (url === '/library/imported') return { entries: [], kanji: [] }
      return []
    })
    const { default: EntryPage } = await import('../../app/pages/library/entries/[id].vue')
    // Its tooltips need UApp.
    const wrapper = await mountSuspended(
      defineComponent({ render: () => h(UApp, null, { default: () => h(EntryPage) }) }),
      { route: '/library/entries/7' },
    )
    await flushPromises()

    const kanjiFetches = () => api.mock.calls.filter(([url]) => String(url).startsWith('/dictionary/kanji/')).length
    expect(kanjiFetches()).toBe(2) // 三 and 匹

    const reading = wrapper.findAll('[data-testid="form-item"]').find(row => row.text().includes('さんびき'))!
    await reading.find('[role="switch"]').trigger('click')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/library/entries/7/readings/2/enabled', { method: 'PUT', body: { enabled: false } })
    expect(kanjiFetches()).toBe(2)
  })
})
