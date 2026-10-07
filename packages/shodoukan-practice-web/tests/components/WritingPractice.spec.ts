// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount, flushPromises } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { clearNuxtData } from '#app'
import { FetchError } from 'ofetch'
import FreeWritingPad from '../../app/components/FreeWritingPad.vue'
import GuidedWritingPad from '../../app/components/GuidedWritingPad.vue'
import WritingPractice from '../../app/components/WritingPractice.vue'
import { signedInAuth } from '../fakes'
import { stubResizeObserver } from '../resize-observer'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
enableAutoUnmount(afterEach)

const ICHI = [{ path: 'M14,54c20,0,60,0,80,0', label: null }]

beforeEach(() => {
  clearNuxtData()
  stubResizeObserver()
  api.mockReset()
  api.mockImplementation(async (url: string) => {
    if (url.endsWith(`/${encodeURIComponent('〆')}/strokes`)) {
      throw Object.assign(new FetchError('404 Not Found'), { statusCode: 404 })
    }
    return { literal: '?', strokes: ICHI }
  })
})
afterEach(() => vi.unstubAllGlobals())

async function practice(chars: string[], mode = 'guided-free', repetitions = 1, items = chars.map(text => ({ text }))) {
  const wrapper = await mountSuspended(WritingPractice, { props: { items, mode, repetitions } })
  await flushPromises()
  return wrapper
}

const text = (wrapper: Awaited<ReturnType<typeof practice>>, id: string) => wrapper.get(`[data-testid="${id}"]`).text()

describe('WritingPractice', () => {
  it('guides a character once, then lets it be drawn freely, then goes on', async () => {
    const wrapper = await practice(['一', '二'])
    expect(text(wrapper, 'practice-text')).toBe('一')
    expect(text(wrapper, 'practice-step')).toBe('Guiado')
    expect(text(wrapper, 'practice-progress')).toBe('1 / 2')
    expect(wrapper.find('[data-testid="practice-next-row"]').exists()).toBe(false)

    wrapper.findComponent(GuidedWritingPad).vm.$emit('done')
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    await flushPromises()

    expect(wrapper.findComponent(FreeWritingPad).exists()).toBe(true)
    expect(text(wrapper, 'practice-step')).toBe('Libre · 1 de 1')

    wrapper.findComponent(FreeWritingPad).vm.$emit('done')
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    await flushPromises()

    expect(text(wrapper, 'practice-text')).toBe('二')
    expect(text(wrapper, 'practice-progress')).toBe('2 / 2')
  })

  it('starts a drawing over with Otra vez', async () => {
    const wrapper = await practice(['一'], 'free')
    const first = wrapper.findComponent(FreeWritingPad).vm
    first.$emit('done')
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-testid="practice-again"]').trigger('click')

    expect(wrapper.findComponent(FreeWritingPad).vm).not.toBe(first)
    expect(wrapper.find('[data-testid="practice-next-row"]').exists()).toBe(false)
  })

  it('passes over a character without a drawing, and finishes after the last', async () => {
    const wrapper = await practice(['〆', '一'], 'guided-free', 2)
    expect(wrapper.find('[data-testid="practice-missing"]').exists()).toBe(true)

    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    await flushPromises()
    expect(text(wrapper, 'practice-text')).toBe('一')
    expect(text(wrapper, 'practice-step')).toBe('Guiado')

    for (let i = 0; i < 3; i++) {
      wrapper.findComponent(i ? FreeWritingPad : GuidedWritingPad).vm.$emit('done')
      await wrapper.vm.$nextTick()
      await wrapper.get('[data-testid="practice-next"]').trigger('click')
      await flushPromises()
    }
    expect(wrapper.emitted('finished')).toHaveLength(1)
  })

  it('writes a word one character after another, with a row of cells', async () => {
    const wrapper = await practice([], 'free', 1, [{ text: '一〆二', reading: 'いち' }])
    expect(text(wrapper, 'practice-text')).toBe('一〆二')
    expect(text(wrapper, 'practice-reading')).toBe('いち')
    const cells = () => wrapper.findAll('[data-testid="practice-cell"]')
    expect(cells().map(c => c.text())).toEqual(['一', '〆', '二'])
    expect(cells()[0]!.attributes('aria-current')).toBe('step')
    expect(cells()[1]!.attributes('disabled')).toBeDefined()

    wrapper.findComponent(FreeWritingPad).vm.$emit('done')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[data-testid="practice-next"]').exists()).toBe(false)
    await wrapper.get('[data-testid="practice-next-cell"]').trigger('click')
    await flushPromises()

    // 〆 has no drawing: shown, then on to the next character.
    expect(cells()[1]!.attributes('aria-current')).toBe('step')
    expect(wrapper.find('[data-testid="practice-missing"]').exists()).toBe(true)
    await wrapper.get('[data-testid="practice-next-cell"]').trigger('click')
    await flushPromises()

    wrapper.findComponent(FreeWritingPad).vm.$emit('done')
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    expect(wrapper.emitted('finished')).toHaveLength(1)
  })

  it('draws a done character of a word again from its cell', async () => {
    const wrapper = await practice([], 'free', 1, [{ text: '一二' }])
    wrapper.findComponent(FreeWritingPad).vm.$emit('done')
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="practice-next-cell"]').trigger('click')
    await flushPromises()

    await wrapper.findAll('[data-testid="practice-cell"]')[0]!.trigger('click')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="practice-cell"]')[0]!.attributes('aria-current')).toBe('step')
    expect(wrapper.find('[data-testid="practice-next-row"]').exists()).toBe(false)
  })
})
