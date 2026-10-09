// @vitest-environment nuxt
import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import MeaningList from '../../app/components/MeaningList.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

const meanings = [
  { id: 1, text: 'to eat', enabled: true, origin: 'imported' as const },
  { id: 2, text: 'to scoff', enabled: false, origin: 'added' as const },
]

describe('MeaningList', () => {
  it('offers edit and delete only for the user\'s own meanings', async () => {
    const wrapper = await mountSuspended(MeaningList, { props: { meanings } })

    const rows = wrapper.findAll('[data-testid="meaning"]')
    expect(rows).toHaveLength(2)
    expect(rows[0]!.find('[data-testid="edit"]').exists()).toBe(false)
    expect(rows[0]!.find('[data-testid="remove"]').exists()).toBe(false)
    expect(rows[1]!.find('[data-testid="edit"]').exists()).toBe(true)
    expect(rows[1]!.text()).toContain('propio')
  })

  it('emits toggle and remove, and saves a new meaning', async () => {
    const onAdd = vi.fn().mockResolvedValue(true)
    const wrapper = await mountSuspended(MeaningList, { props: { meanings, onAdd } })

    await wrapper.findAll('[role="switch"]')[0]!.trigger('click')
    await wrapper.find('[data-testid="remove"]').trigger('click')
    await wrapper.find('form input').setValue('  to gobble  ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.emitted('toggle')).toEqual([[1, false]])
    expect(wrapper.emitted('remove')).toEqual([[2]])
    expect(onAdd).toHaveBeenCalledWith('to gobble')
    expect((wrapper.find('form input').element as HTMLInputElement).value).toBe('')
  })

  it('keeps a new meaning\'s text when it isn\'t saved', async () => {
    const onAdd = vi.fn().mockResolvedValue(false)
    const wrapper = await mountSuspended(MeaningList, { props: { meanings, onAdd } })

    await wrapper.find('form input').setValue('to gobble')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(onAdd).toHaveBeenCalledOnce()
    expect((wrapper.find('form input').element as HTMLInputElement).value).toBe('to gobble')
  })

  it('does not add an empty meaning', async () => {
    const onAdd = vi.fn().mockResolvedValue(true)
    const wrapper = await mountSuspended(MeaningList, { props: { meanings: [], onAdd } })

    await wrapper.find('form input').setValue('   ')
    await wrapper.find('form').trigger('submit')

    expect(onAdd).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Sin significados')
  })

  it('edits an own meaning on Enter, and stays editing if it isn\'t saved', async () => {
    const onEdit = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    const wrapper = await mountSuspended(MeaningList, { props: { meanings, onEdit } })

    await wrapper.find('[data-testid="edit"]').trigger('click')
    const input = wrapper.findAll('[data-testid="meaning"]')[1]!.find('input')
    await input.setValue('to wolf down')
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(onEdit).toHaveBeenCalledWith(2, 'to wolf down')
    const stillEditing = wrapper.findAll('[data-testid="meaning"]')[1]!.find('input')
    expect((stillEditing.element as HTMLInputElement).value).toBe('to wolf down')

    await stillEditing.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(onEdit).toHaveBeenCalledTimes(2)
    expect(wrapper.findAll('[data-testid="meaning"]')[1]!.find('input').exists()).toBe(false)
  })

  it('lists only the shown meanings, with no controls, in view-only mode', async () => {
    const wrapper = await mountSuspended(MeaningList, { props: { meanings, viewOnly: true } })

    const rows = wrapper.findAll('[data-testid="meaning"]')
    expect(rows.map(row => row.text())).toEqual(['to eat'])
    expect(wrapper.find('[role="switch"]').exists()).toBe(false)
    expect(wrapper.find('form').exists()).toBe(false)
  })
})
