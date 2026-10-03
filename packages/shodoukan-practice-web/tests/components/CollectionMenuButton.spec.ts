// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import CollectionMenuButton from '../../app/components/CollectionMenuButton.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

const collection = (id: number, name: string) => ({ id, name, description: null, created_at: '', updated_at: '' })
const verbos = collection(1, 'Verbos')
const n5 = collection(2, 'N5')

// The user has "Verbos" and "N5"; library entry 7 is in "N5".
function fakeBackend() {
  api.mockImplementation(async (url: string) => {
    if (url === '/collections/entries') return [verbos, n5]
    if (url === '/library/entries/7/collections') return [n5]
    return undefined
  })
}

// UTooltip and UPopover need what UApp gives the real app; the popover's
// content is portalled to the body.
async function mountOpen(props: Record<string, unknown>) {
  const wrapper = await mountSuspended(defineComponent({
    render: () => h(UApp, null, { default: () => h(CollectionMenuButton, { kind: 'entries', ...props }) }),
  }), { attachTo: document.body })
  await wrapper.find('button').trigger('click')
  await flushPromises()
  const checkbox = (name: string) => {
    const label = [...document.body.querySelectorAll('label')].find(l => l.textContent?.trim() === name)
    return document.getElementById(label!.htmlFor) as HTMLButtonElement
  }
  return {
    checkbox,
    emitted: () => wrapper.findComponent(CollectionMenuButton).emitted('import'),
  }
}

beforeEach(() => {
  api.mockReset()
  document.body.innerHTML = ''
  fakeBackend()
})

describe('CollectionMenuButton', () => {
  it('ticks the collections an imported item is in', async () => {
    const { checkbox } = await mountOpen({ practiceId: 7 })

    expect(checkbox('N5').getAttribute('aria-checked')).toBe('true')
    expect(checkbox('Verbos').getAttribute('aria-checked')).toBe('false')
  })

  it('asks to import an item that is not imported yet into the ticked collection', async () => {
    const { checkbox, emitted } = await mountOpen({})

    expect(api).not.toHaveBeenCalledWith('/library/entries/7/collections')
    checkbox('Verbos').click()
    await flushPromises()

    expect(emitted()).toEqual([[verbos]])
    expect(api).not.toHaveBeenCalledWith('/collections/entries/1/items/7', expect.anything())
  })

  it('adds and removes an imported item', async () => {
    const { checkbox, emitted } = await mountOpen({ practiceId: 7 })

    checkbox('Verbos').click()
    await flushPromises()
    checkbox('N5').click()
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/collections/entries/1/items/7', { method: 'PUT' })
    expect(api).toHaveBeenCalledWith('/collections/entries/2/items/7', { method: 'DELETE' })
    expect(emitted()).toBeUndefined()
  })

  it('says when there are no collections yet', async () => {
    api.mockResolvedValue([])
    await mountOpen({})

    expect(document.body.textContent).toContain('Aún no tienes colecciones.')
    expect(document.body.textContent).toContain('Nueva colección')
  })
})
