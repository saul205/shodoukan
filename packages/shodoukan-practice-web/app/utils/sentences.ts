// Example sentences carry one sentence per language: Japanese ("jpn") and
// translations in ISO 639-2 codes ("eng", "spa", …).

interface Sentence {
  lang: string
  text: string
}

export function japaneseSentence(sentences: Sentence[]): string {
  return sentences.find(s => s.lang === 'jpn')?.text ?? ''
}

export function translatedSentence(sentences: Sentence[], glossLang: string): string {
  return sentences.find(s => s.lang === glossLang)?.text ?? ''
}
