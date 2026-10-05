// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import { signedInAuth } from '../fakes'
import { practiceStatistics, totals } from '../fixtures-statistics'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

async function mountPage(route = '/statistics') {
  const { default: Page } = await import('../../app/pages/statistics/index.vue')
  const wrapper = await mountSuspended(Page, { route })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  api.mockReset()
  clearNuxtData()
})

describe('statistics page', () => {
  it('asks for the window in this browser\'s time zone and shows everything', async () => {
    api.mockResolvedValue(practiceStatistics())

    const wrapper = await mountPage('/statistics?days=7')

    const [url, options] = api.mock.calls[0]!
    expect(url).toBe('/statistics')
    expect(options.query.days).toBe(7)
    expect(options.query.tz).toBe(Intl.DateTimeFormat().resolvedOptions().timeZone)
    expect(wrapper.findAll('[data-testid="activity-day"]')).toHaveLength(3)
    expect(wrapper.find('[data-testid="exercises-table"] tbody').text()).toContain('N5')
    expect(wrapper.findAll('[data-testid="missed-item"]').map(i => i.text())).toEqual([expect.stringContaining('食べる')])
  })

  it('lists the kanji missed most on their tab', async () => {
    api.mockResolvedValue(practiceStatistics())

    const wrapper = await mountPage('/statistics?tab=kanji')

    expect(wrapper.findAll('[data-testid="missed-item"]')).toHaveLength(2)
  })

  it('says when there is nothing to count yet', async () => {
    api.mockResolvedValue(practiceStatistics({
      totals: totals({ sessions: 0, answered: 0, correct: 0, accuracy: null, mean_response_ms: null }),
      exercises: [],
      most_missed_entries: [],
      most_missed_kanji: [],
    }))

    const wrapper = await mountPage()

    expect(wrapper.text()).toContain('Aún no hay nada que contar')
    expect(wrapper.find('[data-testid="activity-chart"]').exists()).toBe(false)
  })
})
