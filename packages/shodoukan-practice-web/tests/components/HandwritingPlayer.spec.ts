// @vitest-environment nuxt
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { KanjiDrawingPad } from 'shodoukan-ui'
import HandwritingPlayer from '../../app/components/exercise-players/HandwritingPlayer.vue'
import { signedInAuth } from '../fakes'
import { drawingQuestion, drawn } from '../fixtures-sessions'

const { createModal, openModal } = vi.hoisted(() => ({ createModal: vi.fn(), openModal: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useOverlay', () => () => ({
  create: (...args: unknown[]) => {
    createModal(...args)
    return { open: openModal }
  },
}))
enableAutoUnmount(afterEach)

// Every measured box is `room` (wide, like a desktop panel), as soon as it's observed.
let room = { width: 800, height: 400 }
beforeEach(() => {
  room = { width: 800, height: 400 }
  vi.stubGlobal('ResizeObserver', class {
    constructor(private callback: ResizeObserverCallback) {}
    observe() {
      this.callback([{ contentRect: room } as ResizeObserverEntry], this as unknown as ResizeObserver)
    }
    unobserve() {}
    disconnect() {}
  })
})
afterEach(() => vi.unstubAllGlobals())

function press(key: string, init: KeyboardEventInit = {}) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...init }))
}

const STROKE: [number, number][] = [[10, 54], [90, 52]]

async function mountWithDrawing(strokes: [number, number][][] = [STROKE]) {
  const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawingQuestion(1) } })
  wrapper.findComponent(KanjiDrawingPad).vm.$emit('update:modelValue', strokes)
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('HandwritingPlayer', () => {
  it('shows the prompt and a pad, and checks only once something is drawn', async () => {
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawingQuestion(1) } })

    expect(wrapper.find('[data-testid="front"]').text()).toContain('one')
    expect(wrapper.find('[data-testid="drawing-pad"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="submit"]').attributes('disabled')).toBeDefined()
    press('Enter')
    expect(wrapper.emitted('answer')).toBeUndefined()
  })

  it('sends the strokes with Comprobar or Enter, and measures the time', async () => {
    const wrapper = await mountWithDrawing()

    press('Enter')

    const [[answer, ms]] = wrapper.emitted('answer') as [[unknown, number]]
    expect(answer).toEqual({ type: 'strokes', strokes: [STROKE] })
    expect(ms).toBeGreaterThanOrEqual(0)
  })

  it('undoes with Backspace or Ctrl+Z, and clears', async () => {
    const wrapper = await mountWithDrawing([STROKE, STROKE, STROKE])

    press('Backspace')
    press('z', { ctrlKey: true })
    await wrapper.vm.$nextTick()
    expect(wrapper.findComponent(KanjiDrawingPad).props('modelValue')).toHaveLength(1)

    await wrapper.get('[data-testid="clear"]').trigger('click')
    expect(wrapper.findComponent(KanjiDrawingPad).props('modelValue')).toEqual([])
  })

  it('skips with S', async () => {
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawingQuestion(1) } })

    press('s')

    expect((wrapper.emitted('answer') as [[unknown]])[0]![0]).toEqual({ type: 'skip' })
  })

  it('ignores answers while busy', async () => {
    const wrapper = await mountWithDrawing()
    await wrapper.setProps({ busy: true })

    press('Enter')

    expect(wrapper.emitted('answer')).toBeUndefined()
  })

  it('once drawn, shows the verdict, the score, the comparison and what was wrong', async () => {
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawn(drawingQuestion(1), 'close') } })

    expect(wrapper.get('[data-testid="verdict"]').text()).toContain('Mejorable')
    expect(wrapper.get('[data-testid="score"]').text()).toContain('71')
    expect(wrapper.find('[data-testid="stroke-comparison"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="stroke-problems"]').text()).toContain('Trazo 1: en sentido contrario.')
    expect(wrapper.find('[data-testid="drawing-pad"]').exists()).toBe(false)

    press('Enter')
    expect(wrapper.emitted('next')).toEqual([[]])
  })

  it('opens the kanji asked for in a practice, over the session', async () => {
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawn(drawingQuestion(1), 'wrong') } })

    await wrapper.get('[data-testid="practise"]').trigger('click')

    expect(openModal).toHaveBeenCalledWith({ items: [{ kind: 'kanji', id: 10 }], title: 'Practicar 一' })
    // Removed once closed, so they don't pile up over a session.
    expect(createModal).toHaveBeenCalledWith(expect.anything(), { destroyOnClose: true })
  })

  it('says a right drawing is right', async () => {
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawn(drawingQuestion(1)) } })

    expect(wrapper.get('[data-testid="verdict"]').text()).toContain('¡Correcto!')
    expect(wrapper.find('[data-testid="stroke-problems"]').exists()).toBe(false)
  })

  it('makes the pad the largest square that fits, not the full width', async () => {
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawingQuestion(1) } })

    expect(wrapper.findComponent(KanjiDrawingPad).props('size')).toBe('400px')
  })

  it('draws no pad until its room is measured', async () => {
    room = { width: 0, height: 0 }
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawingQuestion(1) } })

    expect(wrapper.findComponent(KanjiDrawingPad).exists()).toBe(false)
  })

  it('fits the comparison in the room left once drawn', async () => {
    const wrapper = await mountSuspended(HandwritingPlayer, { props: { question: drawn(drawingQuestion(1)) } })

    const comparison = wrapper.findComponent({ name: 'StrokeComparison' })
    expect(comparison.props('size')).toBe('376px') // two squares in 800, under a caption in 400
    expect(comparison.props('phoneSize')).toBe('360px')
  })

  it("doesn't undo or clear while the drawing is being sent", async () => {
    const wrapper = await mountWithDrawing([STROKE, STROKE])
    await wrapper.setProps({ busy: true })

    press('Backspace')
    press('z', { ctrlKey: true })
    await wrapper.vm.$nextTick()

    expect(wrapper.findComponent(KanjiDrawingPad).props('modelValue')).toHaveLength(2)
  })

  it('caps the drawing at what the server takes, and says so', async () => {
    const wrapper = await mountWithDrawing(Array.from({ length: 40 }, () => STROKE))

    const pad = wrapper.findComponent(KanjiDrawingPad)
    expect(pad.props('maxStrokes')).toBe(40)
    expect(pad.props('maxPoints')).toBe(300)
    expect(wrapper.get('[data-testid="stroke-limit"]').text()).toContain('40 trazos')
  })
})
