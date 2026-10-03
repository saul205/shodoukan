// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { FetchError } from 'ofetch'
import CollectionFormModal from '../../app/components/CollectionFormModal.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

function conflict() {
  const error = new FetchError('409 Conflict')
  Object.assign(error, { statusCode: 409 })
  return error
}

async function mountOpen(props: Record<string, unknown>) {
  const wrapper = await mountSuspended(CollectionFormModal, { props: { ...props, open: true }, attachTo: document.body })
  await flushPromises()
  const form = document.body.querySelector('form#collection-form') as HTMLFormElement
  const input = form.querySelector('input') as HTMLInputElement
  return { wrapper, form, input }
}

async function submit(form: HTMLFormElement) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))
  await flushPromises()
  await new Promise(resolve => setTimeout(resolve, 0))
  await flushPromises()
}

beforeEach(() => {
  api.mockReset()
  document.body.innerHTML = ''
})

describe('CollectionFormModal', () => {
  it('creates a collection and closes with it', async () => {
    const created = { id: 1, name: 'Verbos', description: null }
    api.mockResolvedValue(created)
    const { wrapper, form, input } = await mountOpen({ kind: 'entries' })

    input.value = '  Verbos '
    input.dispatchEvent(new Event('input'))
    await submit(form)

    expect(api).toHaveBeenCalledWith('/collections/entries', {
      method: 'POST',
      body: { name: 'Verbos', description: null },
    })
    expect(wrapper.emitted('close')).toEqual([[created]])
  })

  it('requires a name', async () => {
    const { wrapper, form } = await mountOpen({ kind: 'kanji' })

    await submit(form)

    expect(api).not.toHaveBeenCalled()
    expect(wrapper.emitted('close')).toBeUndefined()
    expect(document.body.textContent).toContain('Ponle un nombre.')
  })

  it('shows a taken name on the name field', async () => {
    api.mockRejectedValue(conflict())
    const { wrapper, form, input } = await mountOpen({ kind: 'entries' })

    input.value = 'Verbos'
    input.dispatchEvent(new Event('input'))
    await submit(form)

    expect(wrapper.emitted('close')).toBeUndefined()
    expect(document.body.textContent).toContain('Ya tienes una colección con ese nombre.')
  })
})
