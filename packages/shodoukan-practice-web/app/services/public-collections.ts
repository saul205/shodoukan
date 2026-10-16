import type { Page } from 'shodoukan-ui'
import type {
  CollectionImport,
  ItemKind,
  PracticeEntry,
  PracticeKanji,
  PublicCollection,
  PublicCollectionQuery,
} from '../models/practice'
import type { ApiClient } from '../utils/api-client'

// Public collections: `/public-collections/entries` and `/public-collections/kanji`
// have the same shape. A private one is a 404, to its owner too.

export function searchPublicCollections(
  api: ApiClient,
  kind: ItemKind,
  query: PublicCollectionQuery = {},
): Promise<Page<PublicCollection>> {
  return api<Page<PublicCollection>>(`/public-collections/${kind}`, { query })
}

export function getPublicCollection(api: ApiClient, kind: ItemKind, id: number): Promise<PublicCollection> {
  return api<PublicCollection>(`/public-collections/${kind}/${id}`)
}

/**
 * A page of its published version, as importing it would give it. The items
 * aren't stored: their ids only tell them apart on the page.
 */
export function previewPublicEntries(
  api: ApiClient,
  id: number,
  query: { limit?: number, offset?: number } = {},
): Promise<Page<PracticeEntry>> {
  return api<Page<PracticeEntry>>(`/public-collections/entries/${id}/items`, { query })
}

export function previewPublicKanji(
  api: ApiClient,
  id: number,
  query: { limit?: number, offset?: number } = {},
): Promise<Page<PracticeKanji>> {
  return api<Page<PracticeKanji>>(`/public-collections/kanji/${id}/items`, { query })
}

/** Import its latest version as a new collection of the user's. */
export function importPublicCollection(api: ApiClient, kind: ItemKind, id: number): Promise<CollectionImport> {
  return api<CollectionImport>(`/public-collections/${kind}/${id}/import`, { method: 'POST' })
}
