// @vitest-environment nuxt
import { afterEach, describe, expect, it, vi } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import FreeCell from '../../app/components/FreeCell.vue'
import WordComparison from '../../app/components/WordComparison.vue'
import WordHandwritingPlayer from '../../app/components/exercise-players/WordHandwritingPlayer.vue'
import { signedInAuth } from '../fakes'
import { wordQuestion, writtenWord } from '../fixtures-sessions'
import { stubResizeObserver } from '../resize-observer'

const { createModal, openModal } = vi.hoisted(() => ({ createModal: vi.fn(), openModal: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useOverlay', () => () => ({
  create: (...args: unknown[]) => {
    createModal(...args)
    return { open: openModal }
  },
}))
enableAutoUnmount(afterEach)
afterEach(() => vi.unstubAllGlobals())

const STROKE: [number, number][] = [[10, 54], [90, 52]]

function press(key: string, init: KeyboardEventInit = {}) {
  window.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true, ...init }))
}

async function player(room = { width: 900, height: 300 }, question = wordQuestion(1)) {
  stubResizeObserver(room)
  const wrapper = await mountSuspended(WordHandwritingPlayer, { props: { question } })
  await wrapper.vm.$nextTick()
  return wrapper
}

describe('WordHandwritingPlayer', () => {
  it('shows a cell per character, in a row on a PC and two columns on a phone', async () => {
    const pc = await player()
    expect(pc.findAllComponents(FreeCell)).toHaveLength(2)
    expect(pc.get('[data-testid="cells-grid"]').attributes('data-columns')).toBe('2')
    // Nothing of the solution: no model under the cells.
    expect(pc.find('[data-model]').exists()).toBe(false)

    const narrow = await player({ width: 150, height: 600 })
    expect(narrow.get('[data-testid="cells-grid"]').attributes('data-columns')).toBe('1')
  })

  it('writes one cell at a time when they would be too small', async () => {
    const wrapper = await player({ width: 200, height: 150 })

    expect(wrapper.findAllComponents(FreeCell)).toHaveLength(1)
    expect(wrapper.findAll('[data-testid="cell-button"]')).toHaveLength(2)
  })

  it('sends every cell with one Comprobar, and only once something is drawn', async () => {
    const wrapper = await player()
    expect(wrapper.get('[data-testid="submit"]').attributes('disabled')).toBeDefined()

    wrapper.findAllComponents(FreeCell)[1]!.vm.$emit('update:modelValue', [STROKE])
    await wrapper.vm.$nextTick()
    press('Enter')

    const [[answer, ms]] = wrapper.emitted('answer') as [[unknown, number]]
    expect(answer).toEqual({ type: 'cells', cells: [[], [STROKE]] })
    expect(ms).toBeGreaterThanOrEqual(0)
  })

  it('undoes and clears the cell last touched, and skips with S', async () => {
    const wrapper = await player()
    const second = wrapper.findAllComponents(FreeCell)[1]!
    second.vm.$emit('touch')
    second.vm.$emit('update:modelValue', [STROKE, STROKE])
    await wrapper.vm.$nextTick()

    await wrapper.get('[data-testid="undo"]').trigger('click')
    expect(wrapper.findAllComponents(FreeCell)[1]!.props('modelValue')).toEqual([STROKE])
    await wrapper.get('[data-testid="clear"]').trigger('click')
    expect(wrapper.findAllComponents(FreeCell)[1]!.props('modelValue')).toEqual([])

    press('s')
    expect((wrapper.emitted('answer') as [[unknown]])[0]![0]).toEqual({ type: 'skip' })
  })

  it('once written, shows the verdict and each character, and practises the word', async () => {
    const wrapper = await player(undefined, writtenWord(wordQuestion(1), 'close'))

    expect(wrapper.get('[data-testid="verdict"]').text()).toContain('Mejorable')
    expect(wrapper.get('[data-testid="score"]').text()).toContain('82')
    const comparison = wrapper.findComponent(WordComparison)
    expect(comparison.findAll('[data-testid="cell-result"]').map(c => c.text())).toEqual(['み92', 'ず71'])

    await comparison.findAll('[data-testid="cell-result"]')[1]!.trigger('click')
    expect(comparison.get('[data-testid="stroke-problems"]').text()).toContain('Trazo 1: en sentido contrario.')

    await wrapper.get('[data-testid="practise"]').trigger('click')
    expect(openModal).toHaveBeenCalledWith({ items: [{ kind: 'entry', id: 12 }], title: 'Practicar みず' })
    expect(createModal).toHaveBeenCalledWith(expect.anything(), { destroyOnClose: true })

    press('Enter')
    expect(wrapper.emitted('next')).toEqual([[]])
  })
})
