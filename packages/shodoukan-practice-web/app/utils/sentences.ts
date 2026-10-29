import type { PracticeSentence } from '~/models/practice'

// A dictionary example's sentences (one per language: Japanese "jpn" and
// translations in ISO 639-2 codes), and the library's sentences: their
// translations and their words' gaps.

interface LangText {
  lang: string
  text: string
}

export function japaneseSentence(sentences: LangText[]): string {
  return sentences.find(s => s.lang === 'jpn')?.text ?? ''
}

export function translatedSentence(sentences: LangText[], glossLang: string): string {
  return sentences.find(s => s.lang === glossLang)?.text ?? ''
}

/** The translation in `glossLang` (ISO 639-2), or ''. */
export function sentenceTranslation(sentence: PracticeSentence, glossLang: string): string {
  return sentence.translations.find(t => t.lang === glossLang)?.text ?? ''
}

export interface SentencePiece {
  text: string
  /** Part of a word's gap: `own` when it's the word `entryId` asked for. */
  gap: 'own' | 'other' | null
}

/**
 * The sentence cut at its gaps, to highlight them: the gap of the word linked
 * to `entryId` is `own`, the others `other`. Without `entryId` (a preview, whose
 * sentences aren't linked yet) every gap is `own`.
 */
export function sentencePieces(sentence: PracticeSentence, entryId?: number | null): SentencePiece[] {
  const gaps = sentence.words
    .filter(w => w.start !== null && w.end !== null)
    .map(w => ({ start: w.start as number, end: w.end as number, own: entryId == null || w.entry_id === entryId }))
    .sort((a, b) => a.start - b.start)
  const pieces: SentencePiece[] = []
  let at = 0
  for (const gap of gaps) {
    if (gap.start < at) continue
    if (gap.start > at) pieces.push({ text: sentence.text.slice(at, gap.start), gap: null })
    pieces.push({ text: sentence.text.slice(gap.start, gap.end), gap: gap.own ? 'own' : 'other' })
    at = gap.end
  }
  if (at < sentence.text.length) pieces.push({ text: sentence.text.slice(at), gap: null })
  return pieces
}

/** The sentences under each sense of a word: by the sense its word is linked to, the first one when none. */
export function sentencesBySense(
  sentences: PracticeSentence[],
  entryId: number,
  senseIds: number[],
): Map<number, PracticeSentence[]> {
  const bySense = new Map<number, PracticeSentence[]>(senseIds.map(id => [id, []]))
  for (const sentence of sentences) {
    const word = sentence.words.find(w => w.entry_id === entryId)
    const senseId = word?.sense_id != null && bySense.has(word.sense_id) ? word.sense_id : senseIds[0]
    if (senseId !== undefined) bySense.get(senseId)!.push(sentence)
  }
  return bySense
}
