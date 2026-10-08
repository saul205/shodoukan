// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import ExampleList from '../../app/components/ExampleList.vue'
import type { PracticeExample } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

const examples: PracticeExample[] = [
  {
    id: 1, text: '食べる', enabled: true, origin: 'imported',
    sentences: [{ lang: 'jpn', text: 'ご飯を食べる。' }, { lang: 'eng', text: 'I eat rice.' }],
  },
  {
    id: 2, text: '', enabled: false, origin: 'added',
    sentences: [{ lang: 'jpn', text: '朝ご飯を食べた。' }, { lang: 'spa', text: 'Desayuné.' }],
  },
]

describe('ExampleList', () => {
  it('offers edit and delete only for the user\'s own examples', async () => {
    const wrapper = await mountSuspended(ExampleList, { props: { examples, glossLang: 'spa' } })

    const rows = wrapper.findAll('[data-testid="example"]')
    expect(rows[0]!.find('[data-testid="edit-example"]').exists()).toBe(false)
    expect(rows[1]!.text()).toContain('propio')
    expect(rows[1]!.text()).toContain('Desayuné.')

    await rows[0]!.find('[role="switch"]').trigger('click')
    await rows[1]!.find('[data-testid="remove-example"]').trigger('click')

    expect(wrapper.emitted('toggle')).toEqual([[1, false]])
    expect(wrapper.emitted('remove')).toEqual([[2]])
  })

  it('adds an example with an optional translation', async () => {
    const wrapper = await mountSuspended(ExampleList, { props: { examples: [], glossLang: 'eng' } })

    await wrapper.find('[data-testid="add-example"]').trigger('click')
    const inputs = wrapper.findAll('[data-testid="example-form"] input')
    await inputs[0]!.setValue('  水を飲む。 ')
    await wrapper.find('[data-testid="example-form"]').trigger('submit')

    expect(wrapper.emitted('add')).toEqual([['水を飲む。', null]])
    expect(wrapper.find('[data-testid="example-form"]').exists()).toBe(false)
  })

  it('rewrites an own example, starting from its sentence and translation', async () => {
    const wrapper = await mountSuspended(ExampleList, { props: { examples, glossLang: 'spa' } })

    await wrapper.find('[data-testid="edit-example"]').trigger('click')
    const inputs = wrapper.findAll('[data-testid="example-form"] input')
    expect((inputs[0]!.element as HTMLInputElement).value).toBe('朝ご飯を食べた。')
    expect((inputs[1]!.element as HTMLInputElement).value).toBe('Desayuné.')
    await inputs[1]!.setValue('Desayuné pronto.')
    await wrapper.find('[data-testid="example-form"]').trigger('submit')

    expect(wrapper.emitted('edit')).toEqual([[2, '朝ご飯を食べた。', 'Desayuné pronto.']])
  })

  it('lists only the shown examples, with no controls, in view-only mode', async () => {
    const wrapper = await mountSuspended(ExampleList, { props: { examples, glossLang: 'eng', viewOnly: true } })

    expect(wrapper.findAll('[data-testid="example"]')).toHaveLength(1)
    expect(wrapper.find('[role="switch"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="add-example"]').exists()).toBe(false)
  })
})
