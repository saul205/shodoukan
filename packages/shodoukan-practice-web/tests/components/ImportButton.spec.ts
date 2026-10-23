// @vitest-environment nuxt
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import ImportButton from '../../app/components/ImportButton.vue'
import { signedInAuth } from '../fakes'

mockNuxtImport('useAuth', () => signedInAuth)

// UTooltip needs the TooltipProvider that UApp gives the real app.
async function mountButton(props: Record<string, unknown>) {
  const wrapper = await mountSuspended(defineComponent({
    render: () => h(UApp, null, { default: () => h(ImportButton, props) }),
  }))
  return {
    button: () => wrapper.find('button'),
    emitted: (event: 'import' | 'remove') => wrapper.findComponent(ImportButton).emitted(event),
  }
}

describe('ImportButton', () => {
  it('imports a result that is not in the library', async () => {
    const { button, emitted } = await mountButton({ imported: false })

    expect(button().text()).toBe('Importar')
    expect(button().attributes('aria-label')).toBe('Importar a tu librería')
    await button().trigger('click')
    expect(emitted('import')).toHaveLength(1)
    expect(emitted('remove')).toBeUndefined()
  })

  it('turns "in your library" into "remove" on hover and removes on click', async () => {
    const { button, emitted } = await mountButton({ imported: true })

    expect(button().text()).toBe('En tu librería')
    await button().trigger('mouseenter')
    expect(button().text()).toBe('Quitar')
    expect(button().attributes('aria-label')).toBe('Quitar de tu librería')
    await button().trigger('click')
    expect(emitted('remove')).toHaveLength(1)
    expect(emitted('import')).toBeUndefined()

    await button().trigger('mouseleave')
    expect(button().text()).toBe('En tu librería')
  })

  it('shows "remove" on keyboard focus too', async () => {
    const { button } = await mountButton({ imported: true })
    await button().trigger('focus')
    expect(button().text()).toBe('Quitar')
  })

  it('has no visible label when icon-only, only the aria-label', async () => {
    const { button } = await mountButton({ imported: false, iconOnly: true })
    expect(button().text()).toBe('')
    expect(button().attributes('aria-label')).toBe('Importar a tu librería')
  })

  it('passes classes to the button (the tooltip renders no element)', async () => {
    const { button } = await mountButton({ imported: false, iconOnly: true, class: 'absolute top-2 right-2' })
    expect(button().classes()).toContain('absolute')
  })
})
