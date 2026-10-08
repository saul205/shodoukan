import { getDictionaryKanjiStrokes } from '~/services/dictionary'
import { apiStatus } from '~/utils/api-error'

// A character's strokes (KanjiVG, from the practice API), cached by
// character. One without a drawing (404) gives `null` strokes. While another
// character loads, `useAsyncData` keeps the previous one's data: those are
// never handed out as this one's, and the status stays pending.
export function useKanjiStrokes(literal: MaybeRefOrGetter<string>) {
  const api = useApi()
  const { data, status } = useAsyncData(
    () => `kanji-strokes-${toValue(literal)}`,
    async () => {
      const requested = toValue(literal)
      try {
        return { literal: requested, strokes: (await getDictionaryKanjiStrokes(api, requested)).strokes }
      }
      catch (error) {
        if (apiStatus(error) === 404) return { literal: requested, strokes: null }
        throw error
      }
    },
    { watch: [() => toValue(literal)] },
  )
  const current = computed(() => (data.value?.literal === toValue(literal) ? data.value : null))
  const strokes = computed(() => current.value?.strokes ?? null)
  const loading = computed(() => (current.value ? status.value : status.value === 'error' ? 'error' : 'pending'))
  return { strokes, status: loading }
}
