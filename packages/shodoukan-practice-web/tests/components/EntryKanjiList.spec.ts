// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { UApp } from '#components'
import EntryKanjiList from '../../app/components/EntryKanjiList.vue'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

function kanji(literal: string) {
  return { literal, grade: null, stroke_count: 7, freq: null, jlpt: null, on_readings: [], kun_readings: [], nanori: [], meanings: [] }
}

// 兄 is in the library as practice kanji 3; the rest aren't. UTooltip needs UApp.
async function mountList(literals: string[], linkTo?: 'dictionary' | 'library') {
  const wrapper = await mountSuspended(defineComponent({
    setup() {
      const status = useImportStatus()
      status.kanji.value = new Map([['兄', 3]])
      return () => h(UApp, null, {
        default: () => h(EntryKanjiList, { kanji: literals.map(kanji), status, linkTo }),
      })
    },
  }))
  return {
    hrefs: () => wrapper.findAll('a').map(a => a.attributes('href')),
    text: () => wrapper.text(),
  }
}

beforeEach(() => {
  api.mockReset()
})

describe('EntryKanjiList', () => {
  it('opens imported kanji in the library when it links to the library', async () => {
    const { hrefs } = await mountList(['兄', '弟'], 'library')
    expect(hrefs()).toEqual(['/library/kanji/3', `/dictionary/kanji/弟`])
  })

  it('links every kanji to the dictionary by default', async () => {
    const { hrefs } = await mountList(['兄', '弟'])
    expect(hrefs()).toEqual([`/dictionary/kanji/兄`, `/dictionary/kanji/弟`])
  })

  it('offers to import the missing ones only when more than one is missing', async () => {
    expect((await mountList(['兄', '弟'])).text()).not.toContain('que faltan')
    expect((await mountList(['兄', '弟', '姉'])).text()).toContain('Importar los 2 que faltan')
  })
})
