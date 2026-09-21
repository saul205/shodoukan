import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import KanjiCard from '../../components/KanjiCard.vue'
import type { Kanji } from '../../models/kanji'

const kanji: Kanji = {
  literal: '食',
  grade: 2,
  stroke_count: 9,
  freq: 316,
  jlpt: 4,
  on_readings: ['ショク', 'ジキ'],
  kun_readings: ['た.べる'],
  nanori: [],
  meanings: [
    { text: 'eat', lang: 'en' },
    { text: 'food', lang: 'en' },
    { text: 'comer', lang: 'es' },
  ],
}

describe('KanjiCard', () => {
  it('renders the kanji literal', () => {
    const wrapper = mount(KanjiCard, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).toContain('食')
  })

  it('shows meanings for the selected language', () => {
    const wrapper = mount(KanjiCard, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).toContain('eat')
    expect(wrapper.text()).toContain('food')
  })

  it('excludes meanings for other languages', () => {
    const wrapper = mount(KanjiCard, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).not.toContain('comer')
  })

  it('shows Spanish meanings when lang is es', () => {
    const wrapper = mount(KanjiCard, { props: { kanji, lang: 'es' } })
    expect(wrapper.text()).toContain('comer')
    expect(wrapper.text()).not.toContain('eat')
  })

  it('shows JLPT badge', () => {
    const wrapper = mount(KanjiCard, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).toContain('N4')
  })

  it('shows stroke count', () => {
    const wrapper = mount(KanjiCard, { props: { kanji, lang: 'en' } })
    expect(wrapper.text()).toContain('9 strokes')
  })

  it('shows dash when no meanings exist for language', () => {
    const wrapper = mount(KanjiCard, { props: { kanji, lang: 'de' } })
    expect(wrapper.text()).toContain('—')
  })
})
