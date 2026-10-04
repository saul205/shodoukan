import { describe, expect, it, vi } from 'vitest'
import { addToCollection, listCollectionEntries, listCollectionKanji, updateCollection } from '../../app/services/collections'
import { searchDictionary } from '../../app/services/dictionary'
import {
  addGloss,
  getImportStatus,
  importEntry,
  listLibraryEntries,
  listLibraryKanji,
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
    await importEntry(api, 1000002, [4])
    await setEntryPartEnabled(api, 3, 'kanji-readings', 7, false)
    await addGloss(api, 3, 5, 'to scoff', 'eng')
    await setKanjiNotes(api, 4, null)

    expect(calls).toEqual([
      ['/library/entries', { method: 'POST', body: { entry_id: 1000001, collection_ids: [] } }],
      ['/library/entries', { method: 'POST', body: { entry_id: 1000002, collection_ids: [4] } }],
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
    await listCollectionEntries(api, 1, { active: false })

    expect(calls).toEqual([
      ['/collections/kanji/2', { method: 'PUT', body: { name: 'N5', description: null } }],
      ['/collections/entries/1/items/9', { method: 'PUT' }],
      ['/collections/entries/1/items', { query: { limit: 10, offset: 10 } }],
      ['/collections/entries/1/items', { query: { active: false } }],
    ])
  })

  it('library and collection lists send the search', async () => {
    const { api, calls } = fakeApi()
    await listLibraryEntries(api, { q: 'taberu', meaning_lang: 'eng', not_in_collection: 3, limit: 20, offset: 0 })
    await listLibraryKanji(api, { q: '兄弟', active: true })
    await listCollectionKanji(api, 4, { q: 'eat', meaning_lang: 'en' })

    expect(calls).toEqual([
      ['/library/entries', { query: { q: 'taberu', meaning_lang: 'eng', not_in_collection: 3, limit: 20, offset: 0 } }],
      ['/library/kanji', { query: { q: '兄弟', active: true } }],
      ['/collections/kanji/4/items', { query: { q: 'eat', meaning_lang: 'en' } }],
    ])
  })
})
