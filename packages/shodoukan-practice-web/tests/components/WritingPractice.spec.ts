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

async function practice(chars: string[], mode = 'guided-free', repetitions = 1) {
  const wrapper = await mountSuspended(WritingPractice, { props: { chars, mode, repetitions } })
  await flushPromises()
  return wrapper
}

const text = (wrapper: Awaited<ReturnType<typeof practice>>, id: string) => wrapper.get(`[data-testid="${id}"]`).text()

describe('WritingPractice', () => {
  it('guides a character once, then lets it be drawn freely, then goes on', async () => {
    const wrapper = await practice(['一', '二'])
    expect(text(wrapper, 'practice-char')).toBe('一')
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

    expect(text(wrapper, 'practice-char')).toBe('二')
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
    expect(text(wrapper, 'practice-char')).toBe('一')
    expect(text(wrapper, 'practice-step')).toBe('Guiado')

    for (let i = 0; i < 3; i++) {
      wrapper.findComponent(i ? FreeWritingPad : GuidedWritingPad).vm.$emit('done')
      await wrapper.vm.$nextTick()
      await wrapper.get('[data-testid="practice-next"]').trigger('click')
      await flushPromises()
    }
    expect(wrapper.emitted('finished')).toHaveLength(1)
  })

  it('restarts the same character when the mode changes', async () => {
    const wrapper = await practice(['一', '二', '三'], 'guided-free', 2)
    // 一 guided, then twice free: on to 二, guided (the fourth step).
    for (let i = 0; i < 3; i++) {
      wrapper.findComponent(i ? FreeWritingPad : GuidedWritingPad).vm.$emit('done')
      await wrapper.vm.$nextTick()
      await wrapper.get('[data-testid="practice-next"]').trigger('click')
      await flushPromises()
    }
    expect(text(wrapper, 'practice-char')).toBe('二')

    await wrapper.setProps({ mode: 'guided' })
    await flushPromises()

    expect(text(wrapper, 'practice-char')).toBe('二')
    expect(text(wrapper, 'practice-step')).toBe('Guiado')
  })

  it("doesn't draw the previous character while the next one loads", async () => {
    const wrapper = await practice(['一', '二'], 'free')
    let resolve: (value: unknown) => void = () => {}
    api.mockImplementation(() => new Promise((r) => { resolve = r }))
    wrapper.findComponent(FreeWritingPad).vm.$emit('done')
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-testid="practice-next"]').trigger('click')
    await wrapper.vm.$nextTick()

    expect(text(wrapper, 'practice-char')).toBe('二')
    expect(wrapper.findComponent(FreeWritingPad).exists()).toBe(false)

    resolve({ literal: '二', strokes: ICHI })
    await flushPromises()
    expect(wrapper.findComponent(FreeWritingPad).exists()).toBe(true)
  })
})
