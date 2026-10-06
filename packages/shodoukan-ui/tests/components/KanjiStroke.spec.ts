import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import KanjiStrokeAnimator from '../../src/components/KanjiStrokeAnimator.vue'
import KanjiStrokeDiagram from '../../src/components/KanjiStrokeDiagram.vue'
import KanjiStrokeGrid from '../../src/components/KanjiStrokeGrid.vue'
import type { KanjiStroke } from '../../src/models/kanji'
import { strokeStart } from '../../src/utils/strokes'

// 人: two strokes, as the API returns them.
const strokes: KanjiStroke[] = [
  { path: 'M54.5,15.75c0.12,1.4-0.4,4.5-1.2,7', label: [47.5, 15.5] },
  { path: 'M51.25,44.5c3.25,4,10,12,20,20', label: [62.5, 49.5] },
]

describe('strokeStart', () => {
  it('reads the leading move-to point', () => {
    expect(strokeStart('M54.5,15.75c0.12,1.4')).toEqual([54.5, 15.75])
    expect(strokeStart('M 20 30 L 40 50')).toEqual([20, 30])
  })
})

describe('KanjiStrokeGrid', () => {
  it('draws one frame per stroke, with the strokes so far', () => {
    const wrapper = mount(KanjiStrokeGrid, { props: { strokes } })

    const frames = wrapper.findAll('svg')
    expect(frames).toHaveLength(2)
    expect(frames[0].findAll('path')).toHaveLength(1)
    expect(frames[1].findAll('path').map(p => p.attributes('d'))).toEqual(strokes.map(s => s.path))
    expect(frames[1].get('circle').attributes()).toMatchObject({ cx: '51.25', cy: '44.5' })
  })

  it('sizes its frames from cellSize (6rem by default)', () => {
    const byDefault = mount(KanjiStrokeGrid, { props: { strokes } })
    const small = mount(KanjiStrokeGrid, { props: { strokes, cellSize: '4.5rem' } })

    expect(byDefault.get('.grid').attributes('style')).toContain('minmax(6rem, 1fr)')
    expect(byDefault.get('svg').attributes('style')).toContain('calc(6rem * 2)')
    expect(small.get('.grid').attributes('style')).toContain('minmax(4.5rem, 1fr)')
    expect(small.get('svg').attributes('style')).toContain('calc(4.5rem * 2)')
  })

  it('shows its labels while loading and when there is no drawing', () => {
    const labels = { loadingLabel: 'Cargando…', unavailableLabel: 'No disponible' }
    const loading = mount(KanjiStrokeGrid, { props: { strokes: null, loading: true, ...labels } })
    const missing = mount(KanjiStrokeGrid, { props: { strokes: null, ...labels } })

    expect(loading.text()).toBe('Cargando…')
    expect(missing.text()).toBe('No disponible')
    expect(missing.find('svg').exists()).toBe(false)
  })
})

describe('KanjiStrokeAnimator', () => {
  it('draws at 160 px by default, or at the given size', () => {
    const byDefault = mount(KanjiStrokeAnimator, { props: { strokes } })
    const small = mount(KanjiStrokeAnimator, { props: { strokes, size: 128 } })

    expect(byDefault.get('svg').attributes('style')).toContain('width: 160px')
    expect(small.get('svg').attributes('style')).toContain('height: 128px')
  })

  it('shows the outline until played', () => {
    const wrapper = mount(KanjiStrokeAnimator, { props: { strokes } })
    expect(wrapper.findAll('path')).toHaveLength(2)
    expect(wrapper.find('.kanji-stroke-draw').exists()).toBe(false)
  })

  it('animates the strokes one after another with custom labels', async () => {
    const wrapper = mount(KanjiStrokeAnimator, {
      props: { strokes, playLabel: 'Reproducir', playingLabel: 'Reproduciendo…' },
    })
    const button = wrapper.get('button')
    expect(button.text()).toBe('Reproducir')

    await button.trigger('click')
    const drawn = wrapper.findAll('.kanji-stroke-draw')
    expect(drawn).toHaveLength(2)
    expect(drawn[1].attributes('style')).toContain('animation-delay: 750ms')
    expect(button.text()).toBe('Reproduciendo…')
    expect(button.attributes('disabled')).toBeDefined()

    await drawn[1].trigger('animationend')
    expect(button.text()).toBe('Reproducir')
    expect(wrapper.find('.kanji-stroke-draw').exists()).toBe(false)
    expect(wrapper.findAll('path')).toHaveLength(4) // outline + fully drawn
  })

  it('cannot play without strokes', () => {
    const wrapper = mount(KanjiStrokeAnimator, { props: { strokes: null } })
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    expect(wrapper.find('path').exists()).toBe(false)
  })
})

describe('KanjiStrokeDiagram', () => {
  it('draws every stroke with its number', () => {
    const wrapper = mount(KanjiStrokeDiagram, { props: { strokes, size: 120 } })

    expect(wrapper.findAll('path')).toHaveLength(2)
    const numbers = wrapper.findAll('text')
    expect(numbers.map(t => t.text())).toEqual(['1', '2'])
    expect(numbers[1].attributes()).toMatchObject({ x: '62.5', y: '49.5' })
    expect(wrapper.get('svg').attributes('style')).toContain('width: 120px')
  })
})
