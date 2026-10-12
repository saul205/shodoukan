// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import { FetchError } from 'ofetch'
import CollectionsPage from '../../app/pages/collections/index.vue'
import { signedInAuth } from '../fakes'

const { api, toast } = vi.hoisted(() => ({ api: vi.fn(), toast: { add: vi.fn() } }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
mockNuxtImport('useToast', () => () => toast)
enableAutoUnmount(afterEach)

const verbs = { id: 4, name: 'Verbos', description: null, created_at: '', updated_at: '' }
const kanjiFile = {
  format: 'shodoukan.collection',
  version: 1,
  kind: 'kanji',
  exported_at: null,
  collection: { name: 'N5', items: [{ literal: '日' }] },
}

beforeEach(() => {
  clearNuxtData()
  toast.add.mockReset()
  api.mockReset()
  api.mockImplementation(async (url: string) => {
    if (url === '/collections/entries') return [verbs]
    if (url === '/collections/kanji') return []
    if (url === '/collections/kanji/import') {
      return { collection: { ...verbs, id: 9, name: 'N5' }, created: 1, existing: 0, missing: [] }
    }
    throw new Error(`unexpected ${url}`)
  })
})

async function choose(wrapper: Awaited<ReturnType<typeof mountSuspended>>, text: string) {
  const input = wrapper.get('[data-testid="import-file"]')
  const file = new File([text], 'n5.shodoukan.json', { type: 'application/json' })
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  await flushPromises()
}

/** A failed API call answered with `status`. */
function apiFailure(status: number) {
  const error = new FetchError('failed')
  error.statusCode = status
  return error
}

async function exportFirst(wrapper: Awaited<ReturnType<typeof mountSuspended>>) {
  await wrapper.get('button[aria-label="Acciones"]').trigger('click')
  await flushPromises()
  const item = [...document.querySelectorAll('[role="menuitem"]')].find(el => el.textContent?.includes('Exportar'))
  ;(item as HTMLElement).click()
  await flushPromises()
}

describe('collections page', () => {
  it.each([
    [422, 'La colección tiene demasiados elementos para exportarla.'],
    [500, 'Algo ha fallado. Inténtalo de nuevo.'],
  ])('explains a failed export by its status (%i)', async (status, description) => {
    api.mockImplementation(async (url: string) => {
      if (url === '/collections/entries') return [verbs]
      throw apiFailure(status)
    })
    const wrapper = await mountSuspended(CollectionsPage, { route: '/collections' })
    await flushPromises()

    await exportFirst(wrapper)

    expect(api).toHaveBeenCalledWith('/collections/entries/4/export')
    expect(toast.add).toHaveBeenCalledWith(expect.objectContaining({ title: 'No se ha podido exportar', description }))
  })

  it.each([
    [422, 'El archivo no es válido o está dañado; no se ha importado nada.'],
    [500, 'Algo ha fallado. Inténtalo de nuevo.'],
  ])('explains a failed import by its status (%i)', async (status, description) => {
    api.mockImplementation(async (url: string) => {
      if (url === '/collections/entries') return [verbs]
      throw apiFailure(status)
    })
    const wrapper = await mountSuspended(CollectionsPage, { route: '/collections' })
    await flushPromises()

    await choose(wrapper, JSON.stringify(kanjiFile))

    expect(toast.add).toHaveBeenCalledWith(expect.objectContaining({ title: 'No se ha podido importar', description }))
  })

  it('imports a file into its own kind and says what it did', async () => {
    const wrapper = await mountSuspended(CollectionsPage, { route: '/collections' })
    await flushPromises()

    await choose(wrapper, JSON.stringify(kanjiFile))

    expect(api).toHaveBeenCalledWith('/collections/kanji/import', { method: 'POST', body: kanjiFile })
    expect(toast.add).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Colección «N5» importada',
      description: '1 nuevo, 0 ya estaban en tu librería',
      color: 'success',
    }))
  })

  it('does not send what is not a collection file', async () => {
    const wrapper = await mountSuspended(CollectionsPage, { route: '/collections' })
    await flushPromises()

    await choose(wrapper, '{"hello": 1}')

    expect(api).not.toHaveBeenCalledWith('/collections/entries/import', expect.anything())
    expect(toast.add).toHaveBeenCalledWith(expect.objectContaining({
      title: 'No se puede importar',
      description: 'No es una colección exportada de Shodoukan.',
    }))
  })
})
