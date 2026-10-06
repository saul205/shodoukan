// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { FetchError } from 'ofetch'
import KanjiStrokeOrder from '../../app/components/KanjiStrokeOrder.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

const strokes = {
  literal: '人',
  strokes: [
    { path: 'M54.5,15.75c0.12,1.4-0.4,4.5-1.2,7', label: [47.5, 15.5] },
    { path: 'M51.25,44.5c3.25,4,10,12,20,20', label: [62.5, 49.5] },
  ],
}

async function mountStrokeOrder(literal = '人') {
  const wrapper = await mountSuspended(KanjiStrokeOrder, { props: { literal, size: 128, cellSize: '4.5rem' } })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  api.mockReset()
  clearNuxtData() // the strokes are cached by kanji, as in the app
})

describe('KanjiStrokeOrder', () => {
  it('fetches the strokes once for the animation and the frames', async () => {
    api.mockResolvedValue(strokes)
    const wrapper = await mountStrokeOrder()

    expect(api).toHaveBeenCalledTimes(1)
    expect(api).toHaveBeenCalledWith(`/dictionary/kanji/${encodeURIComponent('人')}/strokes`)
    const svgs = wrapper.findAll('svg')
    expect(svgs).toHaveLength(3) // the animation + one frame per stroke
    expect(svgs[0].attributes('style')).toContain('width: 128px')
    expect(wrapper.html()).toContain('minmax(4.5rem, 1fr)')
    expect(wrapper.get('button').text()).toBe('Reproducir')
  })

  it('says when the kanji has no drawing', async () => {
    api.mockRejectedValue(Object.assign(new FetchError('404 Not Found'), { statusCode: 404 }))
    const wrapper = await mountStrokeOrder('搔')

    expect(wrapper.text()).toContain('Orden de trazos no disponible.')
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
  })

  it('credits KanjiVG', async () => {
    api.mockResolvedValue(strokes)
    const wrapper = await mountStrokeOrder()

    const link = wrapper.findAll('a').find(a => a.text() === 'KanjiVG')
    expect(link?.attributes('href')).toBe('https://kanjivg.tagaini.net/')
    expect(wrapper.text()).toContain('CC BY-SA 3.0')
  })
})
