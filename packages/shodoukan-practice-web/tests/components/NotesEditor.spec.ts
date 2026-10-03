// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import NotesEditor from '../../app/components/NotesEditor.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

describe('NotesEditor', () => {
  it('saves the cleaned note when leaving the field', async () => {
    const wrapper = await mountSuspended(NotesEditor, { props: { notes: null } })
    const textarea = wrapper.find('textarea')

    await textarea.setValue('  ichidan  ')
    await textarea.trigger('blur')

    expect(wrapper.emitted('save')).toEqual([['ichidan']])
  })

  it('does not save when nothing changed', async () => {
    const wrapper = await mountSuspended(NotesEditor, { props: { notes: 'ichidan' } })
    const textarea = wrapper.find('textarea')

    await textarea.setValue('ichidan  ')
    await textarea.trigger('blur')

    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('clearing the text removes the note', async () => {
    const wrapper = await mountSuspended(NotesEditor, { props: { notes: 'old' } })
    const textarea = wrapper.find('textarea')

    await textarea.setValue('   ')
    await textarea.trigger('blur')

    expect(wrapper.emitted('save')).toEqual([[null]])
  })

  it('refuses a note over 2000 characters', async () => {
    const wrapper = await mountSuspended(NotesEditor, { props: { notes: null } })
    const textarea = wrapper.find('textarea')

    await textarea.setValue('x'.repeat(2001))
    await textarea.trigger('blur')

    expect(wrapper.emitted('save')).toBeUndefined()
    expect(wrapper.text()).toContain('demasiado larga')
  })
})
