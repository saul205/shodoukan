import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import KanjiCardCompact from '../../src/components/KanjiCardCompact.vue'
import type { Kanji } from '../../src/models/kanji'

const kanji: Kanji = {
  literal: '食',
  grade: 2,
  stroke_count: 9,
  freq: 316,
  jlpt: 4,
  on_readings: ['ショク'],
  kun_readings: ['た.べる'],
  nanori: [],
  meanings: [
    { text: 'eat', lang: 'en' },
    { text: 'food', lang: 'en' },
    { text: 'comer', lang: 'es' },
  ],
}

describe('KanjiCardCompact', () => {
  it('renders the kanji literal and readings', () => {
    const wrapper = mount(KanjiCardCompact, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).toContain('食')
    expect(wrapper.text()).toContain('た.べる')
    expect(wrapper.text()).toContain('ショク')
  })

  it('shows meanings for the selected language only', () => {
    const wrapper = mount(KanjiCardCompact, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).toContain('eat, food')
    expect(wrapper.text()).not.toContain('comer')
  })

  it('shows the JLPT badge', () => {
    const wrapper = mount(KanjiCardCompact, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).toContain('N4')
  })

  it('renders as a plain <a> by default', () => {
    const wrapper = mount(KanjiCardCompact, { props: { kanji, lang: 'en' } })
    expect(wrapper.find('a').attributes('href')).toBe('/kanji/食')
  })

  it('uses the provided linkComponent with a `to` prop instead of `href`', () => {
    const FakeLink = { props: ['to'], template: '<a :data-to="to"><slot /></a>' }
    const wrapper = mount(KanjiCardCompact, { props: { kanji, lang: 'en', linkComponent: FakeLink } })
    expect(wrapper.find('a').attributes('data-to')).toBe('/kanji/食')
  })
})
