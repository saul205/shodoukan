// @vitest-environment nuxt
import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import EntryDetail from '../../app/components/EntryDetail.vue'
import type { PracticeEntry, PracticeSense } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

function sense(id: number, text: string, extra: Partial<PracticeSense> = {}): PracticeSense {
  return {
    id, pos: [], misc: [], dialects: [], info: [], examples: [], notes: null, enabled: true, origin: 'imported',
    glosses: [{ id: id * 10, text, lang: 'eng', type: null, enabled: true, origin: extra.origin ?? 'imported' }],
    ...extra,
  }
}

const entry: PracticeEntry = {
  id: 1, source_entry_id: 1000, jlpt: null, is_common: false, is_active: true, notes: null, created_at: '', updated_at: '',
  kanji_readings: [{ id: 1, kanji: '食べる', info: [], enabled: true }],
  readings: [{ id: 1, text: 'たべる', no_kanji: false, info: [], restricted_to: [], enabled: true }],
  senses: [sense(1, 'to eat'), sense(2, 'to live on', { enabled: false }), sense(3, 'to dine', { origin: 'added' })],
}

describe('EntryDetail', () => {
  it('switches whole senses and removes only the user\'s own', async () => {
    const wrapper = await mountSuspended(EntryDetail, { props: { entry } })

    const senses = wrapper.findAll('[data-testid="sense"]')
    expect(senses).toHaveLength(3)
    expect(senses[1]!.text()).toContain('oculto al practicar')
    expect(senses[0]!.find('[data-testid="remove-sense"]').exists()).toBe(false)
    expect(senses[2]!.text()).toContain('propio')

    await senses[0]!.find('[data-testid="sense-switch"]').trigger('click')
    await senses[2]!.find('[data-testid="remove-sense"]').trigger('click')

    expect(wrapper.emitted('toggle')).toEqual([['senses', 1, false]])
    expect(wrapper.emitted('remove-sense')).toEqual([[3]])
  })

  it('adds a sense of the user\'s own with its first meaning, keeping it if it isn\'t saved', async () => {
    const onAddSense = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    const wrapper = await mountSuspended(EntryDetail, { props: { entry, onAddSense } })

    const form = wrapper.find('[data-testid="add-sense"]')
    await form.find('input').setValue('   ')
    await form.trigger('submit')
    expect(onAddSense).not.toHaveBeenCalled()

    await form.find('input').setValue('  to feed on  ')
    await form.trigger('submit')
    await flushPromises()
    expect(onAddSense).toHaveBeenCalledWith('to feed on')
    expect((form.find('input').element as HTMLInputElement).value).toBe('  to feed on  ')

    await form.trigger('submit')
    await flushPromises()
    expect(onAddSense).toHaveBeenCalledTimes(2)
    expect((form.find('input').element as HTMLInputElement).value).toBe('')
  })

  it('passes a sense\'s new meanings and examples to the page with the sense', async () => {
    const onAddGloss = vi.fn().mockResolvedValue(true)
    const onAddExample = vi.fn().mockResolvedValue(true)
    const wrapper = await mountSuspended(EntryDetail, { props: { entry, onAddGloss, onAddExample } })

    const own = wrapper.findAll('[data-testid="sense"]')[2]!
    const meaningForm = own.findAll('form').find(f => f.find('input[placeholder^="Añadir un significado propio"]').exists())!
    await meaningForm.find('input').setValue('to have dinner')
    await meaningForm.trigger('submit')
    await own.find('[data-testid="add-example"]').trigger('click')
    await own.find('[data-testid="example-form"] input').setValue('夕食を食べる。')
    await own.find('[data-testid="example-form"]').trigger('submit')
    await flushPromises()

    expect(onAddGloss).toHaveBeenCalledWith(3, 'to have dinner')
    expect(onAddExample).toHaveBeenCalledWith(3, '夕食を食べる。', null)
  })

  it('leaves disabled senses out in view-only mode', async () => {
    const wrapper = await mountSuspended(EntryDetail, { props: { entry, viewOnly: true } })

    expect(wrapper.findAll('[data-testid="sense"]')).toHaveLength(2)
    expect(wrapper.text()).not.toContain('to live on')
    expect(wrapper.find('[data-testid="add-sense"]').exists()).toBe(false)
  })
})
