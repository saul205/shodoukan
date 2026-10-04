import type { Page } from 'shodoukan-ui'
import type {
  Collection,
  EntryPart,
  ImportStatus,
  KanjiPart,
  LibraryQuery,
  PracticeEntry,
  PracticeKanji,
  PracticeUser,
} from '../models/practice'
import type { ApiClient } from '../utils/api-client'

// The user's library. Every edit returns the whole item as it is now.

export function getMe(api: ApiClient): Promise<PracticeUser> {
  return api<PracticeUser>('/users/me')
}

// --- Import ---

// `collectionIds` puts the item in those collections in the same request: if
// one isn't the user's, nothing is imported (404). Idempotent.

export function importEntry(api: ApiClient, entryId: number, collectionIds: number[] = []): Promise<PracticeEntry> {
  return api<PracticeEntry>('/library/entries', {
    method: 'POST',
    body: { entry_id: entryId, collection_ids: collectionIds },
  })
}

export function importKanji(api: ApiClient, literal: string, collectionIds: number[] = []): Promise<PracticeKanji> {
  return api<PracticeKanji>('/library/kanji', { method: 'POST', body: { literal, collection_ids: collectionIds } })
}

/** Which of these dictionary items the user has imported, with their practice ids. */
export function getImportStatus(
  api: ApiClient,
  entryIds: number[],
  literals: string[],
): Promise<ImportStatus> {
  if (!entryIds.length && !literals.length) return Promise.resolve({ entries: [], kanji: [] })
  return api<ImportStatus>('/library/imported', {
    query: { entry_ids: entryIds, literals },
  })
}

// --- Entries ---

export function listLibraryEntries(api: ApiClient, query: LibraryQuery = {}): Promise<Page<PracticeEntry>> {
  return api<Page<PracticeEntry>>('/library/entries', { query })
}

export function getLibraryEntry(api: ApiClient, id: number): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}`)
}

export function removeLibraryEntry(api: ApiClient, id: number): Promise<void> {
  return api(`/library/entries/${id}`, { method: 'DELETE' })
}

export function getEntryCollections(api: ApiClient, id: number): Promise<Collection[]> {
  return api<Collection[]>(`/library/entries/${id}/collections`)
}

export function setEntryActive(api: ApiClient, id: number, active: boolean): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}/active`, { method: 'PUT', body: { active } })
}

export function setEntryNotes(api: ApiClient, id: number, notes: string | null): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}/notes`, { method: 'PUT', body: { notes } })
}

export function setSenseNotes(
  api: ApiClient,
  id: number,
  senseId: number,
  notes: string | null,
): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}/senses/${senseId}/notes`, {
    method: 'PUT',
    body: { notes },
  })
}

export function setEntryPartEnabled(
  api: ApiClient,
  id: number,
  part: EntryPart,
  itemId: number,
  enabled: boolean,
): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}/${part}/${itemId}/enabled`, {
    method: 'PUT',
    body: { enabled },
  })
}

/** `lang` is ISO 639-2 (e.g. "eng"), like the entry's glosses. */
export function addGloss(
  api: ApiClient,
  id: number,
  senseId: number,
  text: string,
  lang: string,
): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}/senses/${senseId}/glosses`, {
    method: 'POST',
    body: { text, lang },
  })
}

export function editGloss(api: ApiClient, id: number, glossId: number, text: string): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}/glosses/${glossId}`, { method: 'PUT', body: { text } })
}

export function removeGloss(api: ApiClient, id: number, glossId: number): Promise<PracticeEntry> {
  return api<PracticeEntry>(`/library/entries/${id}/glosses/${glossId}`, { method: 'DELETE' })
}

// --- Kanji ---

export function listLibraryKanji(api: ApiClient, query: LibraryQuery = {}): Promise<Page<PracticeKanji>> {
  return api<Page<PracticeKanji>>('/library/kanji', { query })
}

export function getLibraryKanji(api: ApiClient, id: number): Promise<PracticeKanji> {
  return api<PracticeKanji>(`/library/kanji/${id}`)
}

export function removeLibraryKanji(api: ApiClient, id: number): Promise<void> {
  return api(`/library/kanji/${id}`, { method: 'DELETE' })
}

export function getKanjiCollections(api: ApiClient, id: number): Promise<Collection[]> {
  return api<Collection[]>(`/library/kanji/${id}/collections`)
}

export function setKanjiActive(api: ApiClient, id: number, active: boolean): Promise<PracticeKanji> {
  return api<PracticeKanji>(`/library/kanji/${id}/active`, { method: 'PUT', body: { active } })
}

export function setKanjiNotes(api: ApiClient, id: number, notes: string | null): Promise<PracticeKanji> {
  return api<PracticeKanji>(`/library/kanji/${id}/notes`, { method: 'PUT', body: { notes } })
}

export function setKanjiPartEnabled(
  api: ApiClient,
  id: number,
  part: KanjiPart,
  itemId: number,
  enabled: boolean,
): Promise<PracticeKanji> {
  return api<PracticeKanji>(`/library/kanji/${id}/${part}/${itemId}/enabled`, {
    method: 'PUT',
    body: { enabled },
  })
}

/** `lang` is ISO 639-1 (e.g. "en"), like the kanji's meanings. */
export function addKanjiMeaning(api: ApiClient, id: number, text: string, lang: string): Promise<PracticeKanji> {
  return api<PracticeKanji>(`/library/kanji/${id}/meanings`, { method: 'POST', body: { text, lang } })
}

export function editKanjiMeaning(
  api: ApiClient,
  id: number,
  meaningId: number,
  text: string,
): Promise<PracticeKanji> {
  return api<PracticeKanji>(`/library/kanji/${id}/meanings/${meaningId}`, { method: 'PUT', body: { text } })
}

export function removeKanjiMeaning(api: ApiClient, id: number, meaningId: number): Promise<PracticeKanji> {
  return api<PracticeKanji>(`/library/kanji/${id}/meanings/${meaningId}`, { method: 'DELETE' })
}
