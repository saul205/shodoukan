// @vitest-environment nuxt
import { afterEach, describe, expect, it } from 'vitest'
import { enableAutoUnmount } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import StrokeComparison from '../../app/components/StrokeComparison.vue'
import type { HandwritingGrade, ReferenceKanji } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

enableAutoUnmount(afterEach)

const references: ReferenceKanji[] = [
  { literal: '二', strokes: [{ path: 'M25,32c20,0,40,-3,54,-3', label: [20, 30] }, { path: 'M12,80c30,0,60,-4,85,-4', label: [8, 78] }] },
  { literal: '三', strokes: [{ path: 'M27,23c20,0,40,-3,58,-3', label: null }] },
]
const grade: HandwritingGrade = {
  score: 60,
  verdict: 'close',
  matched: '二',
  strokes: [
    { drawn: 0, reference: 0, status: 'ok' },
    { drawn: 1, reference: null, status: 'extra' },
    { drawn: null, reference: 1, status: 'missing' },
  ],
}

describe('StrokeComparison', () => {
  it('draws the drawing coloured by grade next to the matched kanji', async () => {
    const wrapper = await mountSuspended(StrokeComparison, {
      props: { drawing: [[[25, 32], [79, 29]], [[50, 50]]], references, grade },
    })

    const reference = wrapper.get('[data-testid="comparison-reference"]')
    expect(reference.findAll('path')).toHaveLength(2)
    expect(reference.findAll('path')[1]!.attributes('style')).toContain('var(--ui-error)')
    expect(wrapper.text()).toContain('二')

    const overlay = wrapper.get('[data-testid="comparison-drawing"]')
    expect(overlay.findAll('[data-ghost] path')).toHaveLength(2)
    const drawnPaths = overlay.findAll('path').slice(2)
    expect(drawnPaths.map(p => p.attributes('d'))).toEqual(['M25,32 L79,29', 'M50,50 l0,0'])
    expect(drawnPaths[0]!.attributes('style')).toContain('var(--ui-success)')
    expect(drawnPaths[1]!.attributes('style')).toContain('var(--ui-error)')
  })

  it('switches the phone view between overlay, drawing and kanji', async () => {
    const wrapper = await mountSuspended(StrokeComparison, {
      props: { drawing: [[[25, 32], [79, 29]]], references, grade },
    })

    const buttons = wrapper.findAll('[role="group"] button')
    await buttons[2]!.trigger('click')
    expect(wrapper.find('[data-testid="comparison-drawing"]').exists()).toBe(false)
    await buttons[1]!.trigger('click')
    expect(wrapper.get('[data-testid="comparison-drawing"]').find('[data-ghost]').exists()).toBe(false)
  })
})
