import type { Entry, Kanji, KanjiStrokes, Page, SearchResult } from 'shodoukan-ui'
import type { ApiClient } from '../utils/api-client'

// The practice API's own dictionary endpoints (public). Same shapes as
// shodoukan-api, so the shodoukan-ui cards render them.

export function searchDictionary(
  api: ApiClient,
  q: string,
  lang = 'en',
  limit = 20,
  offset = 0,
): Promise<SearchResult> {
  return api<SearchResult>('/dictionary/search', { query: { q, lang, limit, offset } })
}

export function getDictionaryEntry(api: ApiClient, id: number): Promise<Entry> {
  return api<Entry>(`/dictionary/entries/${id}`)
}

export function getDictionaryEntryKanji(api: ApiClient, id: number): Promise<Kanji[]> {
  return api<Kanji[]>(`/dictionary/entries/${id}/kanji`)
}

export function getDictionaryKanji(api: ApiClient, literal: string): Promise<Kanji> {
  return api<Kanji>(`/dictionary/kanji/${encodeURIComponent(literal)}`)
}

export function getDictionaryKanjiEntries(
  api: ApiClient,
  literal: string,
  limit = 10,
  offset = 0,
): Promise<Page<Entry>> {
  return api<Page<Entry>>(`/dictionary/kanji/${encodeURIComponent(literal)}/entries`, {
    query: { limit, offset },
  })
}

export function getDictionaryKanjiStrokes(api: ApiClient, literal: string): Promise<KanjiStrokes> {
  return api<KanjiStrokes>(`/dictionary/kanji/${encodeURIComponent(literal)}/strokes`)
}
