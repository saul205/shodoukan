// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import { FetchError } from 'ofetch'
import { signedInAuth } from '../fakes'

const { api, notify } = vi.hoisted(() => ({
  api: vi.fn(),
  notify: { success: vi.fn(), failure: vi.fn() },
}))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)
mockNuxtImport('useNotify', () => () => notify)

// POST /library/kanji answers with the practice copy; ids follow the literal.
const ids: Record<string, number> = { 兄: 1, 弟: 2, 姉: 3 }
function importedKanji(literal: string) {
  return { id: ids[literal], literal }
}

beforeEach(() => {
  api.mockReset()
  notify.success.mockReset()
  notify.failure.mockReset()
})

describe('useImportStatus().addKanjiList', () => {
  it('imports only the missing kanji, with a single notification', async () => {
    const status = useImportStatus()
    status.kanji.value = new Map([['兄', 1]])
    api.mockImplementation(async (_url: string, options: { body: { literal: string } }) =>
      importedKanji(options.body.literal))

    await status.addKanjiList(['兄', '弟', '姉'])

    expect(api).toHaveBeenCalledTimes(2)
    expect([...status.kanji.value]).toEqual([['兄', 1], ['弟', 2], ['姉', 3]])
    expect(notify.success).toHaveBeenCalledExactlyOnceWith('2 kanji añadidos a tu librería')
    expect(notify.failure).not.toHaveBeenCalled()
    expect(status.isBusyKanji('弟')).toBe(false)
  })

  it('keeps the kanji that were imported when another one fails', async () => {
    const status = useImportStatus()
    api.mockImplementation(async (_url: string, options: { body: { literal: string } }) => {
      if (options.body.literal === '姉') throw new FetchError('500 Internal Server Error')
      return importedKanji(options.body.literal)
    })

    await status.addKanjiList(['弟', '姉'])

    expect([...status.kanji.value.keys()]).toEqual(['弟'])
    expect(notify.success).toHaveBeenCalledExactlyOnceWith('Añadido a tu librería')
    expect(notify.failure).toHaveBeenCalledOnce()
    expect(status.isBusyKanji('姉')).toBe(false)
  })
})

describe('useImportStatus().addEntry', () => {
  it('imports into a collection in the same request and names it', async () => {
    const status = useImportStatus()
    api.mockResolvedValue({ id: 7 })

    await status.addEntry(1000001, { id: 4, name: 'Verbos', description: null, created_at: '', updated_at: '' })

    expect(api).toHaveBeenCalledExactlyOnceWith('/library/entries', {
      method: 'POST',
      body: { entry_id: 1000001, collection_ids: [4] },
    })
    expect(status.entries.value.get(1000001)).toBe(7)
    expect(notify.success).toHaveBeenCalledExactlyOnceWith('Añadida a tu librería y a «Verbos»')
  })
})
