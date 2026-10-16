// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import PublishCollectionModal from '../../app/components/PublishCollectionModal.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

const collection = {
  id: 4, name: 'Verbos', description: null, is_public: false, published_version: 0,
  published_at: null, source_collection_id: null, source_version: null, created_at: '', updated_at: '',
}

beforeEach(() => {
  api.mockReset()
  api.mockImplementation(async () => ({ ...collection, is_public: true, published_version: 1 }))
  document.body.innerHTML = ''
})

async function mountOpen(props: Record<string, unknown>) {
  const wrapper = await mountSuspended(PublishCollectionModal, { props: { ...props, open: true }, attachTo: document.body })
  await flushPromises()
  return wrapper
}

function byTestId(id: string) {
  return document.body.querySelector(`[data-testid="${id}"]`) as HTMLElement
}

describe('PublishCollectionModal', () => {
  it('publishes without the notes unless they are ticked', async () => {
    const wrapper = await mountOpen({ kind: 'entries', collection })
    expect(document.body.textContent).toContain('Publicar «Verbos»')

    byTestId('publish-confirm').click()
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/collections/entries/4/publication', { method: 'PUT', body: { include_notes: false } })
    expect(wrapper.emitted('close')?.[0]?.[0]).toMatchObject({ published_version: 1 })
  })

  it('names the next version of a public one and sends the notes when ticked', async () => {
    await mountOpen({ kind: 'kanji', collection: { ...collection, is_public: true, published_version: 2 } })
    expect(document.body.textContent).toContain('Publicar la versión 3 de «Verbos»')

    const notes = byTestId('publish-notes')
    ;(notes.getAttribute('role') === 'checkbox' ? notes : notes.querySelector('[role="checkbox"]') as HTMLElement).click()
    await flushPromises()
    byTestId('publish-confirm').click()
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/collections/kanji/4/publication', { method: 'PUT', body: { include_notes: true } })
  })
})
