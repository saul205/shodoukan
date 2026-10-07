import type { KanjiStroke } from 'shodoukan-ui'
import { getDictionaryKanjiStrokes } from '~/services/dictionary'
import { apiStatus } from '~/utils/api-error'

// The strokes (KanjiVG) of every character of a word, fetched together. A
// character without a drawing (404) gives `null` in its place. While another
// word loads, `useAsyncData` keeps the previous one's data: those are never
// handed out as this one's, and the status stays pending.
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

  const word = () => toValue(chars).join('')
  const { data, status } = useAsyncData(
    () => `word-strokes-${word()}`,
    async () => {
      const requested = word()
      return { word: requested, strokes: await Promise.all(toValue(chars).map(strokesOf)) }
    },
    { watch: [word] },
  )
  const current = computed(() => (data.value?.word === word() ? data.value : null))
  const loading = computed(() => (current.value ? status.value : status.value === 'error' ? 'error' : 'pending'))
  return { strokes: computed(() => current.value?.strokes ?? null), status: loading }
}
