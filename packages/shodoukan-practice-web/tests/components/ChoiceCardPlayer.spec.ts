// @vitest-environment nuxt
import { afterEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import ChoiceCardPlayer from '../../app/components/exercise-players/ChoiceCardPlayer.vue'
import { signedInAuth } from '../fakes'
import { graded, question } from '../fixtures-sessions'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)

function press(key: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key }))
}

describe('ChoiceCardPlayer', () => {
  it('answers with a number key and measures the time', async () => {
    const wrapper = await mountSuspended(ChoiceCardPlayer, { props: { question: question(1) } })

    press('2')
    press('9') // no such option

    const [[answer, ms]] = wrapper.emitted('answer') as [[unknown, number]]
    expect(answer).toEqual({ type: 'option', option: 1 })
    expect(ms).toBeGreaterThanOrEqual(0)
    expect(wrapper.emitted('answer')).toHaveLength(1)
  })

  it('ignores answers while busy', async () => {
    const wrapper = await mountSuspended(ChoiceCardPlayer, { props: { question: question(1), busy: true } })

    press('1')

    expect(wrapper.emitted('answer')).toBeUndefined()
  })

  it('shows the back and goes on with Enter once answered', async () => {
    const wrapper = await mountSuspended(ChoiceCardPlayer, { props: { question: graded(question(1), 2) } })

    expect(wrapper.find('[data-testid="back"]').text()).toContain('た.べる')
    expect(wrapper.find('[data-testid="verdict"]').text()).toBe('Fallada')
    press('1')
    press('Enter')

    expect(wrapper.emitted('answer')).toBeUndefined()
    expect(wrapper.emitted('next')).toEqual([[]])
    await wrapper.find('[data-testid="open-item"]').trigger('click')
    expect(wrapper.emitted('open-item')).toEqual([[10]])
  })

  it('keeps the bottom row before answering, with no verdict or next', async () => {
    const wrapper = await mountSuspended(ChoiceCardPlayer, { props: { question: question(1) } })

    expect(wrapper.find('[data-testid="bottom-row"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="verdict"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="next"]').exists()).toBe(false)
  })
})
