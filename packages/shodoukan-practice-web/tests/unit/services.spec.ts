import { describe, expect, it, vi } from 'vitest'
import { addToCollection, listCollectionEntries, updateCollection } from '../../app/services/collections'
import { searchDictionary } from '../../app/services/dictionary'
import {
  addGloss,
  getImportStatus,
  importEntry,
  setEntryPartEnabled,
  setKanjiNotes,
} from '../../app/services/library'
import type { ApiClient } from '../../app/utils/api-client'

function fakeApi() {
  const api = vi.fn(async () => ({}))
  return { api: api as unknown as ApiClient, calls: api.mock.calls as unknown as [string, Record<string, unknown>?][] }
}

describe('practice API services', () => {
  it('search sends the query and paging', async () => {
    const { api, calls } = fakeApi()
    await searchDictionary(api, '食べる', 'es', 20, 40)
    expect(calls[0]).toEqual(['/dictionary/search', { query: { q: '食べる', lang: 'es', limit: 20, offset: 40 } }])
  })

  it('import status skips the request when there is nothing to ask about', async () => {
    const { api, calls } = fakeApi()
    expect(await getImportStatus(api, [], [])).toEqual({ entries: [], kanji: [] })
    expect(calls).toHaveLength(0)

    await getImportStatus(api, [1, 2], ['食'])
    expect(calls[0]).toEqual(['/library/imported', { query: { entry_ids: [1, 2], literals: ['食'] } }])
  })

  it('library edits use the documented routes', async () => {
    const { api, calls } = fakeApi()
    await importEntry(api, 1000001)
    await setEntryPartEnabled(api, 3, 'kanji-readings', 7, false)
    await addGloss(api, 3, 5, 'to scoff', 'eng')
    await setKanjiNotes(api, 4, null)

    expect(calls).toEqual([
      ['/library/entries', { method: 'POST', body: { entry_id: 1000001 } }],
      ['/library/entries/3/kanji-readings/7/enabled', { method: 'PUT', body: { enabled: false } }],
      ['/library/entries/3/senses/5/glosses', { method: 'POST', body: { text: 'to scoff', lang: 'eng' } }],
      ['/library/kanji/4/notes', { method: 'PUT', body: { notes: null } }],
    ])
  })

  it('collections use the kind in the path', async () => {
    const { api, calls } = fakeApi()
    await updateCollection(api, 'kanji', 2, { name: 'N5', description: null })
    await addToCollection(api, 'entries', 1, 9)
    await listCollectionEntries(api, 1, { limit: 10, offset: 10 })

    expect(calls).toEqual([
      ['/collections/kanji/2', { method: 'PUT', body: { name: 'N5', description: null } }],
      ['/collections/entries/1/items/9', { method: 'PUT' }],
      ['/collections/entries/1/items', { query: { limit: 10, offset: 10 } }],
    ])
  })
})
