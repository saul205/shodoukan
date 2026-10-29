import type { Page } from 'shodoukan-ui'
import type {
  PracticeSentence,
  SentenceDraft,
  SentenceProposal,
  SentenceQuery,
} from '../models/practice'
import type { ApiClient } from '../utils/api-client'

// The sentences of the user's library. Every change returns the whole
// sentence as it is now, its words analyzed.

const URL = '/library/sentences'

export function listSentences(api: ApiClient, query: SentenceQuery = {}): Promise<Page<PracticeSentence>> {
  return api<Page<PracticeSentence>>(URL, { query })
}

/** The sentences of one word of the library. */
export async function sentencesOfEntry(api: ApiClient, entryId: number): Promise<PracticeSentence[]> {
  return (await listSentences(api, { entry_id: entryId, limit: 100 })).items
}

export function getSentence(api: ApiClient, id: number): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}`)
}

/**
 * A sentence of the user's own and an optional translation in `lang` (ISO
 * 639-2), linked to one of their words if `entryId` is given: its gap is found
 * where the word is, inflected or not.
 */
export function addSentence(
  api: ApiClient,
  japanese: string,
  translation: string | null,
  lang: string,
  entryId?: number,
  senseId?: number,
): Promise<PracticeSentence> {
  return api<PracticeSentence>(URL, {
    method: 'POST',
    body: { japanese, translation, lang, entry_id: entryId ?? null, sense_id: senseId ?? null },
  })
}

/** Each text's morphemes and the library words it uses; nothing is stored. */
export function analyzeSentences(api: ApiClient, texts: string[]): Promise<SentenceProposal[]> {
  return api<SentenceProposal[]>(`${URL}/analyze`, { method: 'POST', body: { texts } })
}

/** Store reviewed sentences with their words, all or nothing. */
export function addSentences(api: ApiClient, sentences: SentenceDraft[]): Promise<PracticeSentence[]> {
  return api<PracticeSentence[]>(`${URL}/batch`, { method: 'POST', body: { sentences } })
}

/** Rewrite an own sentence and its translation in `lang`; the others are kept. */
export function rewriteSentence(
  api: ApiClient,
  id: number,
  japanese: string,
  translation: string | null,
  lang: string,
): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}`, { method: 'PUT', body: { japanese, translation, lang } })
}

export function removeSentence(api: ApiClient, id: number): Promise<void> {
  return api<void>(`${URL}/${id}`, { method: 'DELETE' })
}

export function setSentenceActive(api: ApiClient, id: number, active: boolean): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}/active`, { method: 'PUT', body: { active } })
}

export function setSentenceNotes(api: ApiClient, id: number, notes: string | null): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}/notes`, { method: 'PUT', body: { notes } })
}

/** Mark a word (its span), linked to a library word or not. */
export function addSentenceWord(
  api: ApiClient,
  id: number,
  start: number,
  end: number,
  entryId: number | null = null,
): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}/words`, { method: 'POST', body: { start, end, entry_id: entryId } })
}

/** Link a word to a library word (and sense), or unlink it with `entryId` null. */
export function linkSentenceWord(
  api: ApiClient,
  id: number,
  wordId: number,
  entryId: number | null,
  senseId: number | null = null,
): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}/words/${wordId}/link`, {
    method: 'PUT',
    body: { entry_id: entryId, sense_id: senseId },
  })
}

/** The user's lemma and reading (kana) for a word: the analyzer's can be wrong. */
export function correctSentenceWord(
  api: ApiClient,
  id: number,
  wordId: number,
  lemma: string,
  reading: string,
): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}/words/${wordId}/correction`, {
    method: 'PUT',
    body: { lemma, reading },
  })
}

export function removeSentenceWord(api: ApiClient, id: number, wordId: number): Promise<PracticeSentence> {
  return api<PracticeSentence>(`${URL}/${id}/words/${wordId}`, { method: 'DELETE' })
}
