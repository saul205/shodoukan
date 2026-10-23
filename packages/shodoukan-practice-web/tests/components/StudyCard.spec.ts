// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import StudyCard from '../../app/components/StudyCard.vue'
import { signedInAuth } from '../fakes'
import { graded, question } from '../fixtures-sessions'

mockNuxtImport('useAuth', () => signedInAuth)

describe('StudyCard', () => {
  it('shows only the front until answered', async () => {
    const wrapper = await mountSuspended(StudyCard, { props: { question: question(1) } })

    expect(wrapper.find('[data-testid="prompt"]').text()).toContain('食')
    expect(wrapper.find('[data-testid="front"]').text()).toContain("¿Kun'yomi?")
    expect(wrapper.find('[data-testid="back"]').exists()).toBe(false)
  })

  it('turns to the back once answered: headline, answer, then the extras', async () => {
    const answered = graded(question(1), 0)
    answered.back = [...answered.back!, { field: 'meaning', values: ['eat', 'food'] }]
    const wrapper = await mountSuspended(StudyCard, { props: { question: answered } })

    expect(wrapper.find('[data-testid="front"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="back-headline"]').text()).toBe('食')
    expect(wrapper.find('[data-testid="back-answer"]').text()).toContain('た.べる')
    const extras = wrapper.find('[data-testid="back-extras"]').text()
    expect(extras).toContain('eat; food')
    expect(extras).not.toContain('た.べる')
  })

  it('has no extras when the back only repeats the prompt and the answer', async () => {
    const wrapper = await mountSuspended(StudyCard, { props: { question: graded(question(1), 0) } })

    expect(wrapper.find('[data-testid="back-extras"]').exists()).toBe(false)
  })

  it('shows only the back in a compact review card', async () => {
    const wrapper = await mountSuspended(StudyCard, { props: { question: graded(question(1), 2), compact: true } })

    expect(wrapper.find('[data-testid="front"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="back-answer"]').text()).toContain('た.べる')
  })

  it('keeps room for the back from the front, more with extra back fields', async () => {
    const plain = await mountSuspended(StudyCard, { props: { question: question(1) } })
    const extras = await mountSuspended(StudyCard, { props: { question: question(1), backFields: ['onyomi', 'meaning', 'kunyomi'] } })

    const rem = (wrapper: typeof plain) => Number.parseFloat((wrapper.find('[data-testid="study-card"]').element as HTMLElement).style.minHeight)
    expect(rem(plain)).toBeGreaterThan(0)
    // kunyomi is the answer: two extras, not three
    expect(rem(extras) - rem(plain)).toBeCloseTo(0.75 + 0.75 + 2 * 1.75)
  })

  it('reserves nothing in a compact review card', async () => {
    const wrapper = await mountSuspended(StudyCard, { props: { question: graded(question(1), 0), compact: true } })

    expect((wrapper.find('[data-testid="study-card"]').element as HTMLElement).style.minHeight).toBe('')
  })
})
