// @vitest-environment nuxt
import { afterEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import FreeCell from '../../app/components/FreeCell.vue'
import GuidedCell from '../../app/components/GuidedCell.vue'
import WordWritingBoard from '../../app/components/WordWritingBoard.vue'
import { signedInAuth } from '../fakes'
import { stubResizeObserver } from '../resize-observer'

mockNuxtImport('useAuth', () => signedInAuth)
enableAutoUnmount(afterEach)
afterEach(() => vi.unstubAllGlobals())

const ICHI = [{ path: 'M14,54c20,0,60,0,80,0', label: null }]
const PC = { width: 900, height: 300 }
const PHONE = { width: 328, height: 480 }

async function board(room: { width: number; height: number }, guided: boolean, chars = ['一', '二', '三'], strokes: (typeof ICHI | null)[] = chars.map(() => ICHI)) {
  stubResizeObserver(room)
  const wrapper = await mountSuspended(WordWritingBoard, { props: { chars, strokes, guided } })
  await wrapper.vm.$nextTick()
  return wrapper
}

const columns = (wrapper: Awaited<ReturnType<typeof board>>) => wrapper.get('[data-testid="board-grid"]').attributes('data-columns')

describe('WordWritingBoard', () => {
  it('lays a word out in a row on a PC, and in two columns on a phone', async () => {
    const pc = await board(PC, false)
    expect(columns(pc)).toBe('3')
    expect(pc.findAllComponents(FreeCell)).toHaveLength(3)

    const phone = await board(PHONE, false)
    expect(columns(phone)).toBe('2')
    expect(phone.findAllComponents(FreeCell)).toHaveLength(3)
  })

  it('draws one cell at a time when they would be too small, moving without checking', async () => {
    const wrapper = await board({ width: 328, height: 200 }, false, [...'一二三四五六七'])
    expect(wrapper.findAllComponents(FreeCell)).toHaveLength(1)
    expect(wrapper.findAll('[data-testid="board-cell"]')).toHaveLength(7)

    await wrapper.get('[data-testid="board-next"]').trigger('click')

    expect(wrapper.findAll('[data-testid="board-cell"]')[1]!.attributes('aria-current')).toBe('step')
    expect(wrapper.emitted('done')).toBeUndefined()
  })

  it('checks every free cell with one Comprobar', async () => {
    const wrapper = await board(PC, false)
    expect(wrapper.get('[data-testid="check"]').attributes('disabled')).toBeDefined()

    wrapper.findAllComponents(FreeCell)[2]!.vm.$emit('update:modelValue', [[[14, 54], [94, 54]]])
    await wrapper.vm.$nextTick()
    await wrapper.get('[data-testid="check"]').trigger('click')

    expect(wrapper.findAll('[data-testid="free-result"]')).toHaveLength(3)
    expect(wrapper.emitted('done')).toHaveLength(1)
  })

  it('moves on to the next character by itself when guided', async () => {
    const wrapper = await board(PC, true, ['一', '二'])
    expect(wrapper.findAllComponents(GuidedCell)).toHaveLength(1)
    expect(wrapper.findAll('[data-testid="board-pending"]')).toHaveLength(1)

    wrapper.findComponent(GuidedCell).vm.$emit('done')
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('[data-testid="board-done"]')).toHaveLength(1)
    expect(wrapper.findAllComponents(GuidedCell)).toHaveLength(1)
    expect(wrapper.emitted('done')).toBeUndefined()

    wrapper.findComponent(GuidedCell).vm.$emit('done')
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('done')).toHaveLength(1)
    expect(wrapper.get('[data-testid="guided-status"]').text()).toBe('¡Hecho!')
  })

  it('shows a character without a drawing as given, and skips it when guided', async () => {
    const wrapper = await board(PC, true, ['〆', '一'], [null, ICHI])

    expect(wrapper.get('[data-testid="board-given"]').text()).toBe('〆')
    wrapper.findComponent(GuidedCell).vm.$emit('done')
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('done')).toHaveLength(1)
  })
})
