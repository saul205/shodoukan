import { $fetch } from 'ofetch'
import type { SearchResult } from '~/models/search'

export async function search(
  q: string,
  apiBase: string,
  lang = 'en',
  limit = 20,
  offset = 0,
): Promise<SearchResult> {
  return $fetch<SearchResult>(`${apiBase}/search`, {
    params: { q, lang, limit, offset },
  })
}
