import { getDictionaryKanjiStrokes } from '~/services/dictionary'
import { apiStatus } from '~/utils/api-error'

// A character's strokes (KanjiVG, from the practice API), cached by
// character. One without a drawing (404) gives `null` strokes.
export function useKanjiStrokes(literal: MaybeRefOrGetter<string>) {
  const api = useApi()
  const { data, status } = useAsyncData(
    () => `kanji-strokes-${toValue(literal)}`,
    async () => {
      try {
        return await getDictionaryKanjiStrokes(api, toValue(literal))
      }
      catch (error) {
        if (apiStatus(error) === 404) return null
        throw error
      }
    },
    { watch: [() => toValue(literal)] },
  )
  const strokes = computed(() => data.value?.strokes ?? null)
  return { strokes, status }
}
