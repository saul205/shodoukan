// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { FetchError } from 'ofetch'
import { clearNuxtData } from '#app'
import { signedInAuth } from '../fakes'
import { graded, question, session } from '../fixtures-sessions'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

async function mountPage(route = '/exercise-sessions/5') {
  const { default: Page } = await import('../../app/pages/exercise-sessions/[id].vue')
  const wrapper = await mountSuspended(Page, { route })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  api.mockReset()
  clearNuxtData() // every test loads the same session key
})

describe('exercise session page', () => {
  it('answers, shows the graded card, then the next question', async () => {
    const first = question(1)
    api.mockImplementation(async (url: string) => {
      if (url === '/exercise-sessions/5') return session()
      if (url === '/exercise-sessions/5/answer')
        return { answered: graded(first, 0), next: question(2, '水'), answered_count: 1, score: 1, finished_at: null }
      throw new Error(url)
    })
    const wrapper = await mountPage()

    await wrapper.findAll('[data-testid="option"]')[0]!.trigger('click')
    await flushPromises()

    const [, options] = api.mock.calls.find(([url]) => url === '/exercise-sessions/5/answer')!
    expect(options.body).toMatchObject({ question_id: 1, answer: { type: 'option', option: 0 } })
    expect(wrapper.find('[data-testid="verdict"]').text()).toBe('¡Correcto!')
    expect(wrapper.find('[data-testid="score"]').text()).toBe('1 / 1')

    await wrapper.find('[data-testid="next"]').trigger('click')
    expect(wrapper.find('[data-testid="prompt"]').text()).toContain('水')
    expect(wrapper.find('[data-testid="verdict"]').exists()).toBe(false)
  })

  it("keeps room on the card for the exercise's back fields", async () => {
    api.mockImplementation(async (url: string) => {
      if (url === '/exercise-sessions/5') return session({ current: question(1) })
      if (url === '/exercises/2') return { id: 2, settings: { back_fields: ['onyomi', 'meaning'] } }
      throw new Error(url)
    })
    const wrapper = await mountPage()

    expect(api).toHaveBeenCalledWith('/exercises/2')
    const card = wrapper.find('[data-testid="study-card"]').element as HTMLElement
    expect(Number.parseFloat(card.style.minHeight)).toBeGreaterThan(11)
  })

  it('loads no exercise when it was deleted', async () => {
    api.mockImplementation(async (url: string) => {
      if (url === '/exercise-sessions/5') return session({ exercise_id: null, current: question(1) })
      throw new Error(url)
    })
    await mountPage()

    expect(api.mock.calls.map(([url]) => url)).toEqual(['/exercise-sessions/5'])
  })

  it('says when no other question can be made', async () => {
    const first = question(1)
    api.mockImplementation(async (url: string) =>
      url === '/exercise-sessions/5'
        ? session()
        : { answered: graded(first, 1), next: null, answered_count: 1, score: 0, finished_at: null },
    )
    const wrapper = await mountPage()

    await wrapper.findAll('[data-testid="option"]')[1]!.trigger('click')
    await flushPromises()
    await wrapper.find('[data-testid="next"]').trigger('click')

    expect(wrapper.find('[data-testid="exhausted"]').exists()).toBe(true)
  })

  it('reloads the session when it changed meanwhile', async () => {
    let loads = 0
    api.mockImplementation(async (url: string) => {
      if (url === '/exercise-sessions/5') {
        loads += 1
        return loads === 1 ? session() : session({ current: null, finished_at: '2026-10-05T09:30:00Z', answered: 3, score: 2 })
      }
      throw Object.assign(new FetchError('409 Conflict'), { statusCode: 409 })
    })
    const wrapper = await mountPage()

    await wrapper.findAll('[data-testid="option"]')[0]!.trigger('click')
    await flushPromises()

    expect(loads).toBe(2)
    expect(wrapper.find('[data-testid="result"]').text()).toContain('3 respondidas · 2 acertadas · 67%')
  })

  it('reviews a finished session, or only its missed questions', async () => {
    const right = graded(question(1), 0)
    const wrong = { ...graded(question(2, '水'), 1), position: 1 }
    const skipped = { ...graded(question(3, '火'), 0), position: 2, answer: { type: 'skip' as const }, is_correct: false }
    const finished = session({
      current: null,
      history: [right, wrong, skipped],
      answered: 3,
      score: 1,
      finished_at: '2026-10-05T09:12:00Z',
    })
    api.mockResolvedValue(finished)

    const all = await mountPage()
    const verdicts = all.findAll('[data-testid="review-verdict"]').map(v => v.text())
    expect(verdicts).toEqual(['Correcta', 'Fallada', 'Saltada'])
    expect(all.find('[data-testid="result-when"]').text()).toContain('12 min')
    expect(all.findAll('[data-testid="review-summary"]')[1]!.text()).toBe('水→た.べるみず')
    expect(all.find('[data-testid="review-detail"]').exists()).toBe(false) // collapsed

    await all.findAll('[data-testid="review-toggle"]')[1]!.trigger('click')
    await flushPromises()
    expect(all.findAll('[data-testid="review-detail"]')).toHaveLength(1)
    await all.find('[data-testid="expand-all"]').trigger('click')
    await flushPromises()
    expect(all.findAll('[data-testid="review-detail"]')).toHaveLength(3)

    // Coming back (from the library) keeps them open.
    all.unmount()
    const again = await mountPage()
    expect(again.findAll('[data-testid="review-detail"]')).toHaveLength(3)

    clearNuxtData()
    const missed = await mountPage('/exercise-sessions/5?filter=missed')
    expect(missed.findAll('[data-testid="review-question"]')).toHaveLength(2)
  })
})
