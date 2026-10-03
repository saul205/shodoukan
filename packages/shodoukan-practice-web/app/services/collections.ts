import type { Page } from 'shodoukan-ui'
import type {
  Collection,
  CollectionInput,
  ItemKind,
  PageQuery,
  PracticeEntry,
  PracticeKanji,
} from '../models/practice'
import type { ApiClient } from '../utils/api-client'

// Collections: `/collections/entries` and `/collections/kanji` have the same shape.

export function listCollections(api: ApiClient, kind: ItemKind): Promise<Collection[]> {
  return api<Collection[]>(`/collections/${kind}`)
}

export function getCollection(api: ApiClient, kind: ItemKind, id: number): Promise<Collection> {
  return api<Collection>(`/collections/${kind}/${id}`)
}

export function createCollection(api: ApiClient, kind: ItemKind, input: CollectionInput): Promise<Collection> {
  return api<Collection>(`/collections/${kind}`, { method: 'POST', body: input })
}

/** Replaces name and description together. */
export function updateCollection(
  api: ApiClient,
  kind: ItemKind,
  id: number,
  input: CollectionInput,
): Promise<Collection> {
  return api<Collection>(`/collections/${kind}/${id}`, { method: 'PUT', body: input })
}

export function deleteCollection(api: ApiClient, kind: ItemKind, id: number): Promise<void> {
  return api(`/collections/${kind}/${id}`, { method: 'DELETE' })
}

export function listCollectionEntries(
  api: ApiClient,
  id: number,
  query: PageQuery = {},
): Promise<Page<PracticeEntry>> {
  return api<Page<PracticeEntry>>(`/collections/entries/${id}/items`, { query })
}

export function listCollectionKanji(
  api: ApiClient,
  id: number,
  query: PageQuery = {},
): Promise<Page<PracticeKanji>> {
  return api<Page<PracticeKanji>>(`/collections/kanji/${id}/items`, { query })
}

/** Idempotent: adding an item that's already there does nothing. */
export function addToCollection(api: ApiClient, kind: ItemKind, id: number, itemId: number): Promise<void> {
  return api(`/collections/${kind}/${id}/items/${itemId}`, { method: 'PUT' })
}

/** Idempotent; the item stays in the library. */
export function removeFromCollection(api: ApiClient, kind: ItemKind, id: number, itemId: number): Promise<void> {
  return api(`/collections/${kind}/${id}/items/${itemId}`, { method: 'DELETE' })
}
