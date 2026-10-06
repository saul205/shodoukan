// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

describe('about page', () => {
  it('credits the data sources in Spanish', async () => {
    const { default: Page } = await import('../../app/pages/about.vue')
    const wrapper = await mountSuspended(Page, { route: '/about' })

    expect(wrapper.text()).toContain('Acerca de')
    expect(wrapper.text()).toContain('Fuentes de datos')
    expect(wrapper.text()).toContain('KanjiVG')
    expect(wrapper.find('a[href="https://jisho.org/"]').exists()).toBe(true)
  })
})
