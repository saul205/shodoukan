import { $fetch } from 'ofetch'
import type { Kanji } from '~/models/kanji'
import type { Page } from '~/models/common'

export interface KanjiSearchParams {
  q?: string
  lang?: string
  grade?: number
  jlpt?: number
  limit?: number
  offset?: number
}

export async function searchKanji(
  params: KanjiSearchParams,
  apiBase: string,
): Promise<Page<Kanji>> {
  return $fetch<Page<Kanji>>(`${apiBase}/kanji/search`, { params })
}

export async function getKanji(literal: string, apiBase: string): Promise<Kanji> {
  return $fetch<Kanji>(`${apiBase}/kanji/${encodeURIComponent(literal)}`)
}
