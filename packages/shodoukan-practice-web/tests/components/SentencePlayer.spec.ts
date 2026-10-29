// @vitest-environment nuxt
import { afterEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import SentencePlayer from '../../app/components/exercise-players/SentencePlayer.vue'
import type { SentenceChoiceQuestion } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)

function fill(answered = false): SentenceChoiceQuestion {
  return {
    type: 'sentence.choice',
    id: 1,
    position: 0,
    prompt_fields: ['meaning'],
    answer_field: 'writing',
    prompt: [{ field: 'meaning', values: ['to eat'] }],
    sentence_id: 3,
    before: 'パンを',
    gap: answered ? '食べた' : null,
    after: '。',
    translation: 'I ate bread.',
    options: ['食べた', '飲んだ', '見た'].map((text, i) => ({ text, item_id: answered ? 10 + i : null })),
    answered,
    item_id: answered ? 10 : null,
    correct_option: answered ? 0 : null,
    back: answered ? [{ field: 'meaning', values: ['to eat'] }, { field: 'writing', values: ['食べる'] }] : null,
    answer: answered ? { type: 'option', option: 1 } : null,
    is_correct: answered ? false : null,
    answered_at: answered ? '2026-10-29T10:00:00Z' : null,
    response_ms: answered ? 900 : null,
  }
}

function press(key: string) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }))
}

describe('SentencePlayer', () => {
  it('shows a blank where the word goes, with its meaning as a hint', async () => {
    const wrapper = await mountSuspended(SentencePlayer, { props: { question: fill() } })

    expect(wrapper.find('[data-testid="sentence"]').text()).toContain('パンを')
    expect(wrapper.find('[data-testid="blank"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="gap"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="hint-field"]').text()).toContain('to eat')
    expect(wrapper.find('[data-testid="translation"]').text()).toBe('I ate bread.')

    press('2')

    expect(wrapper.emitted('answer')![0]![0]).toEqual({ type: 'option', option: 1 })
  })

  it('shows the word in the gap and the verdict once answered', async () => {
    const wrapper = await mountSuspended(SentencePlayer, { props: { question: fill(true) } })

    expect(wrapper.find('[data-testid="gap"]').text()).toBe('食べた')
    expect(wrapper.find('[data-testid="verdict"]').text()).toBe('Fallada')
    expect(wrapper.find('[data-testid="hint-field"]').exists()).toBe(false)
    press('Enter')
    expect(wrapper.emitted('next')).toEqual([[]])
  })

  it('underlines the word when its reading is asked', async () => {
    const reading: SentenceChoiceQuestion = {
      ...fill(),
      prompt_fields: ['writing'],
      answer_field: 'reading',
      prompt: [{ field: 'writing', values: ['食べる'] }],
      gap: '食べた',
      options: ['たべた', 'のんだ'].map(text => ({ text, item_id: null })),
    }
    const wrapper = await mountSuspended(SentencePlayer, { props: { question: reading } })

    expect(wrapper.find('[data-testid="gap"]').text()).toBe('食べた')
    expect(wrapper.find('[data-testid="sentence-card"]').text()).toContain('Lectura de la palabra')
  })
})
