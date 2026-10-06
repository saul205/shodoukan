// @vitest-environment nuxt
import { afterEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import ReviewQuestion from '../../app/components/ReviewQuestion.vue'
import { signedInAuth } from '../fakes'
import { drawingQuestion, drawn, graded, question } from '../fixtures-sessions'

const { openModal } = vi.hoisted(() => ({ openModal: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useOverlay', () => () => ({ create: () => ({ open: openModal }) }))
enableAutoUnmount(afterEach)

describe('ReviewQuestion', () => {
  it('sums up a choice card with its wrong pick', async () => {
    const wrapper = await mountSuspended(ReviewQuestion, { props: { question: graded(question(1), 1) } })

    expect(wrapper.get('[data-testid="review-verdict"]').text()).toBe('Fallada')
    expect(wrapper.get('[data-testid="review-summary"]').text()).toContain('た.べる')
    expect(wrapper.get('[data-testid="review-summary"]').text()).toContain('みず')
    expect(wrapper.find('[data-testid="review-thumbnail"]').exists()).toBe(false)
  })

  it('sums up a drawing with its kanji and a thumbnail, and opens to the comparison', async () => {
    const wrapper = await mountSuspended(ReviewQuestion, {
      props: { question: drawn(drawingQuestion(1), 'close'), open: true },
    })

    expect(wrapper.get('[data-testid="review-verdict"]').text()).toBe('Mejorable')
    expect(wrapper.get('[data-testid="review-summary"]').text()).toContain('一')
    expect(wrapper.find('[data-testid="review-thumbnail"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="stroke-comparison"]').exists()).toBe(true)
  })

  it("practises a drawing's kanji from the review, and only a drawing's", async () => {
    const wrapper = await mountSuspended(ReviewQuestion, { props: { question: drawn(drawingQuestion(1), 'wrong'), open: true } })

    await wrapper.get('[data-testid="review-practise"]').trigger('click')
    expect(openModal).toHaveBeenCalledWith({ chars: ['一'] })

    const choice = await mountSuspended(ReviewQuestion, { props: { question: graded(question(1), 1), open: true } })
    expect(choice.find('[data-testid="review-practise"]').exists()).toBe(false)
  })
})
