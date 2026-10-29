// @vitest-environment nuxt
import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import SentenceList from '../../app/components/SentenceList.vue'
import type { PracticeSentence, SentenceWord } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

function word(start: number, end: number, entryId: number | null): SentenceWord {
  return {
    id: start + 1, start, end, lemma: null, reading: null, pos: [], inflection: null,
    entry_id: entryId, sense_id: null,
  }
}

function sentence(id: number, text: string, extra: Partial<PracticeSentence> = {}): PracticeSentence {
  return {
    id, text, translations: [], words: [], is_active: true, notes: null, origin: 'imported',
    created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z', ...extra,
  }
}

const sentences: PracticeSentence[] = [
  sentence(1, 'ご飯を食べる。', {
    translations: [{ lang: 'eng', text: 'I eat rice.' }],
    words: [word(0, 2, 9), word(3, 6, 7)],
  }),
  sentence(2, '朝ご飯を食べた。', {
    origin: 'added',
    is_active: false,
    translations: [{ lang: 'spa', text: 'Desayuné.' }],
  }),
]

describe('SentenceList', () => {
  it('highlights the gap of the word it belongs to', async () => {
    const wrapper = await mountSuspended(SentenceList, { props: { sentences, entryId: 7, glossLang: 'eng' } })

    const gaps = wrapper.findAll('[data-testid="own-gap"]')
    expect(gaps.map(g => g.text())).toEqual(['食べる'])
    expect(wrapper.text()).toContain('I eat rice.')
  })

  it('offers edit and delete only for the user\'s own sentences', async () => {
    const wrapper = await mountSuspended(SentenceList, { props: { sentences, entryId: 7, glossLang: 'spa' } })

    const rows = wrapper.findAll('[data-testid="sentence"]')
    expect(rows[0]!.find('[data-testid="edit-sentence"]').exists()).toBe(false)
    expect(rows[0]!.find('[data-testid="open-sentence"]').attributes('href')).toBe('/library/sentences/1')
    expect(rows[1]!.text()).toContain('propio')
    expect(rows[1]!.text()).toContain('Desayuné.')

    await rows[0]!.find('[role="switch"]').trigger('click')
    await rows[1]!.find('[data-testid="remove-sentence"]').trigger('click')

    expect(wrapper.emitted('toggle')).toEqual([[1, false]])
    expect(wrapper.emitted('remove')).toEqual([[2]])
  })

  it('adds a sentence with an optional translation', async () => {
    const onAdd = vi.fn().mockResolvedValue(true)
    const wrapper = await mountSuspended(SentenceList, { props: { sentences: [], glossLang: 'eng', onAdd } })

    await wrapper.find('[data-testid="add-sentence"]').trigger('click')
    const inputs = wrapper.findAll('[data-testid="sentence-form"] input')
    await inputs[0]!.setValue('  水を飲む。 ')
    await wrapper.find('[data-testid="sentence-form"]').trigger('submit')
    await flushPromises()

    expect(onAdd).toHaveBeenCalledWith('水を飲む。', null)
    expect(wrapper.find('[data-testid="sentence-form"]').exists()).toBe(false)
  })

  it('keeps the form and its text when a sentence isn\'t saved', async () => {
    const onAdd = vi.fn().mockResolvedValue(false)
    const wrapper = await mountSuspended(SentenceList, { props: { sentences: [], glossLang: 'eng', onAdd } })

    await wrapper.find('[data-testid="add-sentence"]').trigger('click')
    const inputs = wrapper.findAll('[data-testid="sentence-form"] input')
    await inputs[0]!.setValue('水を飲む。')
    await inputs[1]!.setValue('I drink water.')
    await wrapper.find('[data-testid="sentence-form"]').trigger('submit')
    await flushPromises()

    const kept = wrapper.findAll('[data-testid="sentence-form"] input')
    expect((kept[0]!.element as HTMLInputElement).value).toBe('水を飲む。')
    expect((kept[1]!.element as HTMLInputElement).value).toBe('I drink water.')
  })

  it('rewrites an own sentence, starting from its text and translation', async () => {
    const onRewrite = vi.fn().mockResolvedValue(true)
    const wrapper = await mountSuspended(SentenceList, { props: { sentences, glossLang: 'spa', onRewrite } })

    await wrapper.find('[data-testid="edit-sentence"]').trigger('click')
    const inputs = wrapper.findAll('[data-testid="sentence-form"] input')
    expect((inputs[0]!.element as HTMLInputElement).value).toBe('朝ご飯を食べた。')
    expect((inputs[1]!.element as HTMLInputElement).value).toBe('Desayuné.')
    await inputs[1]!.setValue('Desayuné pronto.')
    await wrapper.find('[data-testid="sentence-form"]').trigger('submit')
    await flushPromises()

    expect(onRewrite).toHaveBeenCalledWith(2, '朝ご飯を食べた。', 'Desayuné pronto.')
  })

  it('lists only the shown sentences, with no controls, in view-only mode', async () => {
    const wrapper = await mountSuspended(SentenceList, { props: { sentences, glossLang: 'eng', viewOnly: true } })

    expect(wrapper.findAll('[data-testid="sentence"]')).toHaveLength(1)
    expect(wrapper.find('[role="switch"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="add-sentence"]').exists()).toBe(false)
    // No word to highlight: in a preview, every gap is.
    expect(wrapper.findAll('[data-testid="own-gap"]').map(g => g.text())).toEqual(['ご飯', '食べる'])
  })
})
