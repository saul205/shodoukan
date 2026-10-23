// @vitest-environment nuxt
import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import FormList from '../../app/components/FormList.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

const items = [
  { id: 1, text: 'たべる', enabled: true, origin: 'imported' as const },
  { id: 2, text: 'くう', enabled: true, origin: 'added' as const },
]

describe('FormList', () => {
  it('switches every form and deletes only the user\'s own', async () => {
    const wrapper = await mountSuspended(FormList, { props: { items, addLabel: 'Añadir' } })

    const rows = wrapper.findAll('[data-testid="form-item"]')
    expect(rows[0]!.find('[data-testid="remove-form"]').exists()).toBe(false)
    expect(rows[1]!.text()).toContain('propio')

    await rows[0]!.find('[role="switch"]').trigger('click')
    await rows[1]!.find('[data-testid="remove-form"]').trigger('click')

    expect(wrapper.emitted('toggle')).toEqual([[1, false]])
    expect(wrapper.emitted('remove')).toEqual([[2]])
  })

  it('adds only kana when it lists readings', async () => {
    const onAdd = vi.fn().mockResolvedValue(true)
    const wrapper = await mountSuspended(FormList, { props: { items, addLabel: 'Añadir', kana: true, onAdd } })

    await wrapper.find('form input').setValue('kuu')
    await wrapper.find('form').trigger('submit')
    expect(wrapper.text()).toContain('Escríbela en kana')
    await wrapper.find('form input').setValue(' クウ ')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(onAdd).toHaveBeenCalledOnce()
    expect(onAdd).toHaveBeenCalledWith('クウ')
    expect((wrapper.find('form input').element as HTMLInputElement).value).toBe('')
  })

  it('keeps the text when it isn\'t saved', async () => {
    const onAdd = vi.fn().mockResolvedValue(false)
    const wrapper = await mountSuspended(FormList, { props: { items, addLabel: 'Añadir', onAdd } })

    await wrapper.find('form input').setValue('喰う')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect((wrapper.find('form input').element as HTMLInputElement).value).toBe('喰う')
  })
})
