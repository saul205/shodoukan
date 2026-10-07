import type { KanjiStroke } from 'shodoukan-ui'
import { getDictionaryKanjiStrokes } from '~/services/dictionary'
import { apiStatus } from '~/utils/api-error'

// The strokes (KanjiVG) of every character of a word, fetched together. A
// character without a drawing (404) gives `null` in its place.
export function useWordStrokes(chars: MaybeRefOrGetter<string[]>) {
  const api = useApi()

  async function strokesOf(char: string): Promise<KanjiStroke[] | null> {
    try {
      return (await getDictionaryKanjiStrokes(api, char)).strokes
    }
    catch (error) {
      if (apiStatus(error) === 404) return null
      throw error
    }
  }

  const { data, status } = useAsyncData(
    () => `word-strokes-${toValue(chars).join('')}`,
    () => Promise.all(toValue(chars).map(strokesOf)),
    { watch: [() => toValue(chars).join('')] },
  )
  return { strokes: computed(() => data.value ?? null), status }
}
