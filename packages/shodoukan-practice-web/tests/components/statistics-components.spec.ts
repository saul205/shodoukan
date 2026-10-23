// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import AccuracyBar from '../../app/components/AccuracyBar.vue'
import ActivityChart from '../../app/components/ActivityChart.vue'
import MissedItems from '../../app/components/MissedItems.vue'
import TotalsTiles from '../../app/components/TotalsTiles.vue'
import { signedInAuth } from '../fakes'
import { missed, practiceStatistics, totals } from '../fixtures-statistics'

mockNuxtImport('useAuth', () => signedInAuth)

describe('statistics components', () => {
  it('shows the totals, with dashes when there are no answers', async () => {
    const full = await mountSuspended(TotalsTiles, { props: { totals: totals() } })
    expect(full.findAll('[data-testid="stat-value"]').map(v => v.text())).toEqual(['3', '20', '75%', '2,3 s'])

    const empty = await mountSuspended(TotalsTiles, {
      props: { totals: totals({ sessions: 0, answered: 0, correct: 0, accuracy: null, mean_response_ms: null }) },
    })
    expect(empty.findAll('[data-testid="stat-value"]').map(v => v.text())).toEqual(['0', '0', '—', '—'])
  })

  it('writes an accuracy bar as a percentage of the answers', async () => {
    const wrapper = await mountSuspended(AccuracyBar, { props: { label: 'Kanji → Kun\'yomi', correct: 2, answered: 3 } })
    expect(wrapper.text()).toContain('67% · 2/3')
  })

  it('draws one bar per day, scaled to the busiest one', async () => {
    const wrapper = await mountSuspended(ActivityChart, { props: { days: practiceStatistics().activity } })

    const bars = wrapper.findAll('[data-testid="activity-day"]')
    expect(bars).toHaveLength(3)
    const [wrong, right] = bars[2]!.findAll('div')
    expect(wrong!.attributes('style')).toContain('height: 25%')
    expect(right!.attributes('style')).toContain('height: 75%')
    expect(wrapper.find('[role="img"]').attributes('aria-label')).toBe('30 respuestas en 3 días; 2 días con actividad')
  })

  it('opens a missed item', async () => {
    const wrapper = await mountSuspended(MissedItems, { props: { items: [missed(1, '食べる', 'たべる')] } })

    expect(wrapper.text()).toContain('3 de 4')
    await wrapper.find('[data-testid="missed-item"]').trigger('click')
    expect(wrapper.emitted('open-item')).toEqual([[1]])
  })
})
