// @vitest-environment nuxt
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import ItemDetailModal from '../../app/components/ItemDetailModal.vue'
import { useBackLink } from '../../app/composables/useBackLink'
import { signedInAuth } from '../fakes'

const { api, navigate } = vi.hoisted(() => ({ api: vi.fn(), navigate: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
mockNuxtImport('navigateTo', () => navigate)
enableAutoUnmount(afterEach)

describe('ItemDetailModal', () => {
  it('opens the library page in the same window, coming back to the session', async () => {
    api.mockResolvedValue({
      id: 7, literal: '食', grade: 2, stroke_count: 9, freq: null, jlpt: 4,
      on_readings: [], kun_readings: [], nanori: [], meanings: [],
      is_active: true, notes: null, created_at: '', updated_at: '',
    })
    const wrapper = await mountSuspended(ItemDetailModal, {
      props: { kind: 'kanji', itemId: 7, sessionId: 5, open: true },
      attachTo: document.body,
    })
    await flushPromises()

    document.body.querySelector<HTMLElement>('[data-testid="open-in-library"]')!.click()
    await flushPromises()

    expect(wrapper.emitted('close')).toHaveLength(1)
    expect(navigate).toHaveBeenCalledWith({ path: '/library/kanji/7', query: { session: 5 } })
  })
})

describe('useBackLink', () => {
  async function backFrom(route: string) {
    let back: ReturnType<typeof useBackLink> | undefined
    await mountSuspended(defineComponent({
      setup() {
        back = useBackLink('kanji')
        return () => h('div')
      },
    }), { route })
    return back!.value
  }

  it('goes back to the session the item was opened from', async () => {
    expect(await backFrom('/library/kanji/7?session=5')).toEqual({ to: '/exercise-sessions/5', label: 'Volver a la sesión' })
    expect((await backFrom('/library/kanji/7?collection=3')).label).toBe('Volver a la colección')
  })
})
