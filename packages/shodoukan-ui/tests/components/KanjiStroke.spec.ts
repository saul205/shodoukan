import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import KanjiStrokeAnimator from '../../src/components/KanjiStrokeAnimator.vue'
import KanjiStrokeGrid from '../../src/components/KanjiStrokeGrid.vue'

const loadCharacterData = vi.fn()
const animateCharacter = vi.fn()
const create = vi.fn(() => ({ hideCharacter: vi.fn(), animateCharacter }))

vi.mock('hanzi-writer', () => ({ default: { loadCharacterData, create } }))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('KanjiStrokeGrid', () => {
  it('draws one frame per stroke', async () => {
    loadCharacterData.mockResolvedValue({
      strokes: ['M0 0', 'M1 1'],
      medians: [[[0, 0]], [[1, 1]]],
    })
    const wrapper = mount(KanjiStrokeGrid, { props: { literal: '人' } })
    await flushPromises()
    expect(loadCharacterData).toHaveBeenCalledWith('人')
    expect(wrapper.findAll('svg')).toHaveLength(2)
  })

  it('shows its labels while loading and when the data is missing', async () => {
    loadCharacterData.mockRejectedValue(new Error('404'))
    const wrapper = mount(KanjiStrokeGrid, {
      props: { literal: '人', loadingLabel: 'Cargando…', unavailableLabel: 'No disponible' },
    })
    expect(wrapper.text()).toBe('Cargando…')
    await flushPromises()
    expect(wrapper.text()).toBe('No disponible')
  })
})

describe('KanjiStrokeAnimator', () => {
  it('plays the animation with custom labels', async () => {
    const wrapper = mount(KanjiStrokeAnimator, {
      props: { literal: '人', playLabel: 'Reproducir', playingLabel: 'Reproduciendo…' },
    })
    await flushPromises()
    expect(create).toHaveBeenCalled()
    const button = wrapper.get('button')
    expect(button.text()).toBe('Reproducir')

    await button.trigger('click')
    expect(animateCharacter).toHaveBeenCalled()
    expect(button.text()).toBe('Reproduciendo…')
  })
})
