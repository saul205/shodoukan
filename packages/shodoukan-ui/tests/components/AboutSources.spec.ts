import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AboutSources from '../../src/components/AboutSources.vue'

describe('AboutSources', () => {
  it('credits every data source with its licence', () => {
    const wrapper = mount(AboutSources)

    const sources = wrapper.findAll('[data-testid="source"]')
    expect(sources.map(s => s.get('h3').text())).toEqual([
      'JMdict',
      'KANJIDIC2',
      'RADKFILE / KRADFILE',
      'KanjiVG',
      'Tatoeba / Tanaka Corpus',
      'JLPT lists',
    ])
    const kanjivg = sources[3]
    const licence = kanjivg.findAll('a').find(a => a.text() === 'CC BY-SA 3.0')
    expect(licence?.attributes('href')).toBe('https://creativecommons.org/licenses/by-sa/3.0/')
    expect(kanjivg.text()).toContain('Ulrich Apel')
    for (const link of wrapper.findAll('a')) {
      expect(link.attributes('target')).toBe('_blank')
      expect(link.attributes('rel')).toBe('noopener')
    }
  })

  it('names Jisho as its inspiration', () => {
    const wrapper = mount(AboutSources)
    expect(wrapper.find('a[href="https://jisho.org/"]').exists()).toBe(true)
  })

  it('is in English by default and in Spanish with lang="es"', () => {
    expect(mount(AboutSources).text()).toContain('Data sources')
    const spanish = mount(AboutSources, { props: { lang: 'es' } })
    expect(spanish.text()).toContain('Fuentes de datos')
    expect(spanish.text()).toContain('Orden de trazos de kanji y kana')
  })
})
