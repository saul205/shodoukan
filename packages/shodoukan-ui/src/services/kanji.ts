import { $fetch } from 'ofetch'
import type { Kanji, KanjiStrokes } from '../models/kanji'
import type { Page } from '../models/common'

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

/** A character's stroke order, or `null` if there's no drawing for it (404). */
export async function getKanjiStrokes(
  literal: string,
  apiBase: string,
): Promise<KanjiStrokes | null> {
  try {
    return await $fetch<KanjiStrokes>(`${apiBase}/kanji/${encodeURIComponent(literal)}/strokes`)
  }
  catch (error) {
    if ((error as { status?: number }).status === 404) return null
    throw error
  }
}
