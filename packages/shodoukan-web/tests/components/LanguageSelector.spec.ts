import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LanguageSelector from '../../components/LanguageSelector.vue'
import { SUPPORTED_LANGUAGES } from '../../models/kanji'

describe('LanguageSelector', () => {
  it('renders all supported languages', () => {
    const wrapper = mount(LanguageSelector, { props: { modelValue: 'en' } })
    const options = wrapper.findAll('option')
    expect(options).toHaveLength(SUPPORTED_LANGUAGES.length)
    for (const lang of SUPPORTED_LANGUAGES) {
      expect(wrapper.text()).toContain(lang.label)
    }
  })

  it('emits update:modelValue with the selected code on change', async () => {
    const wrapper = mount(LanguageSelector, { props: { modelValue: 'en' } })
    const select = wrapper.find('select')
    await select.setValue('es')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['es'])
  })
})
