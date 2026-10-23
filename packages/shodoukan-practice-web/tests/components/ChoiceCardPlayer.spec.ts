// @vitest-environment nuxt
import { afterEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import ChoiceCardPlayer from '../../app/components/exercise-players/ChoiceCardPlayer.vue'
import { signedInAuth } from '../fakes'
import { graded, question } from '../fixtures-sessions'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)

function press(key: string, init: KeyboardEventInit = {}, target: EventTarget = window) {
  target.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...init }))
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

  it('skips with the button or the S key', async () => {
    const wrapper = await mountSuspended(ChoiceCardPlayer, { props: { question: question(1) } })

    await wrapper.find('[data-testid="skip"]').trigger('click')
    press('s')

    const answers = (wrapper.emitted('answer') as [unknown, number][]).map(([answer]) => answer)
    expect(answers).toEqual([{ type: 'skip' }, { type: 'skip' }])
  })

  it('shows a skipped question as skipped, with only the right option marked', async () => {
    const skipped = { ...graded(question(1), 0), answer: { type: 'skip' as const }, is_correct: false }
    const wrapper = await mountSuspended(ChoiceCardPlayer, { props: { question: skipped } })

    expect(wrapper.find('[data-testid="verdict"]').text()).toBe('Saltada')
    const states = wrapper.findAll('[data-testid="option"]').map(o => o.attributes('data-state'))
    expect(states).toEqual(['correct', 'other', 'other', 'other'])
    expect(wrapper.find('[data-testid="skip"]').exists()).toBe(false)
  })

  it('leaves Enter to a focused control, but not to an option', async () => {
    const wrapper = await mountSuspended(ChoiceCardPlayer, {
      props: { question: graded(question(1), 2) },
      attachTo: document.body,
    })
    const elsewhere = document.createElement('button')
    document.body.append(elsewhere)

    press('Enter', {}, elsewhere)
    expect(wrapper.emitted('next')).toBeUndefined()

    press('Enter', {}, wrapper.find('[data-testid="option"]').element)
    expect(wrapper.emitted('next')).toEqual([[]])
    elsewhere.remove()
  })

  it('ignores shortcuts with modifiers or inside menus and lists', async () => {
    const wrapper = await mountSuspended(ChoiceCardPlayer, {
      props: { question: question(1) },
      attachTo: document.body,
    })
    const list = document.createElement('div')
    list.setAttribute('role', 'listbox')
    const item = document.createElement('div')
    list.append(item)
    document.body.append(list)

    press('s', { ctrlKey: true })
    press('s', { metaKey: true })
    press('Escape', {}, item)
    press('2', {}, item)

    expect(wrapper.emitted('answer')).toBeUndefined()
    list.remove()
  })
})
