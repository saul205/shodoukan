// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import StudyCard from '../../app/components/StudyCard.vue'
import { signedInAuth } from '../fakes'
import { graded, question } from '../fixtures-sessions'

mockNuxtImport('useAuth', () => signedInAuth)

describe('StudyCard', () => {
  it('keeps the back half with a placeholder until answered', async () => {
    const wrapper = await mountSuspended(StudyCard, { props: { question: question(1) } })

    expect(wrapper.find('[data-testid="prompt"]').text()).toContain('食')
    expect(wrapper.find('[data-testid="back-area"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="back-placeholder"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="back"]').exists()).toBe(false)
  })

  it('fills the same back half once answered', async () => {
    const wrapper = await mountSuspended(StudyCard, { props: { question: graded(question(1), 0) } })

    expect(wrapper.find('[data-testid="back-placeholder"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="back-area"] [data-testid="back"]').text()).toContain('た.べる')
  })
})
