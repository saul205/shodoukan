import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EntryCard from '../../src/components/EntryCard.vue'
import type { Entry } from '../../src/models/entry'

const entry: Entry = {
  id: 1,
  kanji_readings: [{ id: 1, kanji: '食べる', priority: [], info: [] }],
  readings: [{ id: 1, text: 'たべる', no_kanji: false, priority: [], info: [], restricted_to: [] }],
  senses: [
    {
      id: 1,
      pos: ['v1'],
      misc: [],
      dialects: [],
      info: [],
      glosses: [
        { id: 1, text: 'to eat', type: null, lang: 'eng' },
        { id: 2, text: 'comer', type: null, lang: 'spa' },
      ],
      cross_references: [],
      examples: [],
    },
  ],
  jlpt: 5,
  is_common: true,
  score: null,
}

describe('EntryCard', () => {
  it('renders the primary form and reading', () => {
    const wrapper = mount(EntryCard, { props: { entry, lang: 'en' } })
    expect(wrapper.text()).toContain('食べる')
    expect(wrapper.text()).toContain('たべる')
  })

  it('shows glosses for the selected language only', () => {
    const wrapper = mount(EntryCard, { props: { entry, lang: 'en' } })
    expect(wrapper.text()).toContain('to eat')
    expect(wrapper.text()).not.toContain('comer')
  })

  it('switches glosses when lang changes', () => {
    const wrapper = mount(EntryCard, { props: { entry, lang: 'es' } })
    expect(wrapper.text()).toContain('comer')
    expect(wrapper.text()).not.toContain('to eat')
  })

  it('shows JLPT and common badges', () => {
    const wrapper = mount(EntryCard, { props: { entry, lang: 'en' } })
    expect(wrapper.text()).toContain('JLPT N5')
    expect(wrapper.text()).toContain('common')
  })

  it('hides badges when neither jlpt nor common apply', () => {
    const wrapper = mount(EntryCard, { props: { entry: { ...entry, jlpt: null, is_common: false }, lang: 'en' } })
    expect(wrapper.text()).not.toContain('JLPT')
    expect(wrapper.text()).not.toContain('common')
  })

  it('renders the details link as a plain <a> by default', () => {
    const wrapper = mount(EntryCard, { props: { entry, lang: 'en' } })
    expect(wrapper.find('a').attributes('href')).toBe('/entry/1')
  })

  it('uses the provided linkComponent with a `to` prop instead of `href`', () => {
    const FakeLink = { props: ['to'], template: '<a :data-to="to"><slot /></a>' }
    const wrapper = mount(EntryCard, { props: { entry, lang: 'en', linkComponent: FakeLink } })
    expect(wrapper.find('a').attributes('data-to')).toBe('/entry/1')
  })

  it('shows a debug score breakdown when score is present', () => {
    const withScore: Entry = { ...entry, score: { freq: 10, jlpt_bonus: 5, exact_match: null, fts_rank: null, sense_pos: null, total_senses: null, composite: null } }
    const wrapper = mount(EntryCard, { props: { entry: withScore, lang: 'en' } })
    expect(wrapper.text()).toContain('freq: 10')
    expect(wrapper.text()).toContain('sort: 15')
  })
})
