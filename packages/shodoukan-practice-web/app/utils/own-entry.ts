// Helpers for the words users write themselves (spellings and readings).

/** Several forms typed in one box, split on commas, 、, ; or spaces, without repeats. */
export function splitForms(text: string): string[] {
  return [...new Set(text.split(/[\s,，、;；]+/).filter(Boolean))]
}

/** Hiragana or katakana only (ー included), as the API takes readings. */
export function isKana(text: string): boolean {
  return /^[ぁ-ヿ]+$/.test(text)
}

/** The kanji in a written form, once each, in order (for its kanji list). */
export function kanjiIn(text: string): string[] {
  return [...new Set([...text].filter(char => /[㐀-鿿豈-﫿]/.test(char)))]
}
