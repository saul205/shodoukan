// @vitest-environment nuxt
import { describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { FetchError } from 'ofetch'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

describe('exercise edit page', () => {
  it('says so when the exercise does not exist', async () => {
    // Behind useAsyncData, which wraps the API's error in its own.
    api.mockRejectedValue(Object.assign(new FetchError('404 Not Found'), { statusCode: 404 }))
    const { default: EditPage } = await import('../../app/pages/exercises/[id]/edit.vue')

    const wrapper = await mountSuspended(EditPage, { route: '/exercises/99/edit' })
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/exercises/99')
    expect(wrapper.text()).toContain('Este ejercicio no existe')
  })
})
