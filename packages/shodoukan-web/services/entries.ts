import { $fetch } from 'ofetch'
import type { Entry, EntryKanjiLink } from '~/models/entry'
import type { Page } from '~/models/common'

export async function searchEntries(
  q: string,
  apiBase: string,
  lang = 'en',
  limit = 20,
  offset = 0,
): Promise<Page<Entry>> {
  return $fetch<Page<Entry>>(`${apiBase}/entries/search`, {
    params: { q, lang, limit, offset },
  })
}

export async function getEntry(id: number, apiBase: string): Promise<Entry> {
  return $fetch<Entry>(`${apiBase}/entries/${id}`)
}

export async function getEntryKanji(id: number, apiBase: string): Promise<EntryKanjiLink[]> {
  return $fetch<EntryKanjiLink[]>(`${apiBase}/entries/${id}/kanji`)
}

export async function getEntriesForKanji(
  literal: string,
  apiBase: string,
  limit = 20,
  offset = 0,
): Promise<Page<Entry>> {
  return $fetch<Page<Entry>>(
    `${apiBase}/entries/by-kanji/${encodeURIComponent(literal)}`,
    { params: { limit, offset } },
  )
}
