import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SearchBar from '../../src/components/SearchBar.vue'

describe('SearchBar', () => {
  it('renders the current modelValue in the input', () => {
    const wrapper = mount(SearchBar, { props: { modelValue: '食べる', lang: 'en' } })
    expect(wrapper.find('input').element.value).toBe('食べる')
  })

  it('emits update:modelValue on input', async () => {
    const wrapper = mount(SearchBar, { props: { modelValue: '', lang: 'en' } })
    await wrapper.find('input').setValue('猫')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['猫'])
  })

  it('emits search on Enter in the input', async () => {
    const wrapper = mount(SearchBar, { props: { modelValue: '猫', lang: 'en' } })
    await wrapper.find('input').trigger('keydown.enter')
    expect(wrapper.emitted('search')).toBeTruthy()
  })

  it('emits search when the button is clicked', async () => {
    const wrapper = mount(SearchBar, { props: { modelValue: '猫', lang: 'en' } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('search')).toBeTruthy()
  })

  it('emits update:lang when the language selector changes', async () => {
    const wrapper = mount(SearchBar, { props: { modelValue: '', lang: 'en' } })
    await wrapper.find('select').setValue('es')
    expect(wrapper.emitted('update:lang')?.[0]).toEqual(['es'])
  })
})
