// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import type { Exercise, SessionSummary } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

const exercise: Exercise = {
  id: 2,
  name: 'N5',
  description: null,
  item_kind: 'kanji',
  collection_ids: [3],
  settings: {
    type: 'card.choice',
    directions: [{ prompt: ['literal'], answer: 'kunyomi' }],
    back_fields: ['meaning'],
    option_count: 4,
    distractor_source: 'collection',
  },
  created_at: '',
  updated_at: '',
}

function summary(id: number, overrides: Partial<SessionSummary> = {}): SessionSummary {
  return {
    id,
    exercise_id: 2,
    exercise_name: 'N5',
    item_kind: 'kanji',
    started_at: '2026-10-05T10:00:00Z',
    last_activity_at: '2026-10-05T10:10:00Z',
    finished_at: '2026-10-05T10:10:00Z',
    answered: 4,
    score: 3,
    ...overrides,
  }
}

function respond(history: SessionSummary[], open: SessionSummary | null) {
  api.mockImplementation(async (url: string, options?: { query?: Record<string, unknown> }) => {
    if (url === '/exercises/2') return exercise
    if (url === '/collections/kanji') return [{ id: 3, name: 'Kanji N5', description: null, created_at: '', updated_at: '' }]
    if (url === '/exercise-sessions' && options?.query?.status === 'open')
      return { items: open ? [open] : [], total: open ? 1 : 0, limit: 1, offset: 0 }
    if (url === '/exercise-sessions') return { items: history, total: history.length, limit: 10, offset: 0 }
    throw new Error(url)
  })
}

async function mountPage() {
  const { default: Page } = await import('../../app/pages/exercises/[id]/index.vue')
  const wrapper = await mountSuspended(Page, { route: '/exercises/2' })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  api.mockReset()
  clearNuxtData()
})

describe('exercise page', () => {
  it('shows the definition and the session history of the exercise', async () => {
    respond([summary(8, { finished_at: null }), summary(7)], null)

    const wrapper = await mountPage()

    expect(wrapper.find('[data-testid="definition"]').text()).toContain('Kanji N5')
    expect(api).toHaveBeenCalledWith('/exercise-sessions', { query: { exercise_id: 2, limit: 10, offset: 0 } })
    const rows = wrapper.findAll('[data-testid="history"] tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.text()).toContain('Abierta')
    expect(rows[1]!.text()).toContain('75%')
    expect(rows[1]!.text()).toContain('10 min')
  })

  it('offers to continue its open session instead of starting', async () => {
    respond([], summary(8, { finished_at: null }))

    const wrapper = await mountPage()

    expect(wrapper.find('[data-testid="resume"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="start"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Aún no has practicado este ejercicio')
  })

  it('starts when the open session is of another exercise', async () => {
    respond([], summary(9, { exercise_id: 5 }))

    const wrapper = await mountPage()

    expect(wrapper.find('[data-testid="start"]').exists()).toBe(true)
  })
})
