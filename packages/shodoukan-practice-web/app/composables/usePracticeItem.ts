import type { PracticeEntry, PracticeKanji } from '~/models/practice'
import { getDictionaryKanji } from '~/services/dictionary'
import { getLibraryEntry, getLibraryKanji } from '~/services/library'
import { apiStatus } from '~/utils/api-error'
import { entryMeanings, kanjiMeanings } from '~/utils/practice-text'
import { entryWriting, type PracticeItem, type PracticeText } from '~/utils/writing-practice'

// What a practice item writes and shows: a library kanji or word with the
// user's own meanings and readings (only what's enabled), or a bare character
// with the dictionary's meanings (none for kana). Items are fetched one at a
// time, as they come up, and the next one ahead. What's fetched is kept only
// for this practice (this call), so a practice started later shows the item
// as it is then: edited, or gone from the library. While another item loads,
// `useAsyncData` keeps the previous one's data: it's never shown as this one's.

type Loaded =
  | { kind: 'kanji'; kanji: PracticeKanji }
  | { kind: 'entry'; entry: PracticeEntry }
  | { kind: 'char'; text: string; meanings: { text: string; lang: string }[] }

/** How many meanings show beside the item. */
const MEANINGS = 3
const KANA = /^[぀-ヿ]$/

function keyOf(item: PracticeItem) {
  return item.kind === 'char' ? `char-${item.text}` : `${item.kind}-${item.id}`
}

export function usePracticeItem(item: MaybeRefOrGetter<PracticeItem | null>, next?: MaybeRefOrGetter<PracticeItem | null>) {
  const api = useApi()
  const { lang, glossCode } = useMeaningLang()
  // This practice's items, fetched or being fetched (the next one ahead).
  const loaded = new Map<string, Promise<Loaded | null>>()

  async function fetchItem(item: PracticeItem): Promise<Loaded | null> {
    try {
      if (item.kind === 'kanji') return { kind: 'kanji', kanji: await getLibraryKanji(api, item.id) }
      if (item.kind === 'entry') return { kind: 'entry', entry: await getLibraryEntry(api, item.id) }
      const meanings = KANA.test(item.text) ? [] : (await getDictionaryKanji(api, item.text)).meanings
      return { kind: 'char', text: item.text, meanings }
    }
    catch (error) {
      // Gone from the library (or not a kanji): nothing to write, or no meanings.
      if (apiStatus(error) !== 404) throw error
      return item.kind === 'char' ? { kind: 'char', text: item.text, meanings: [] } : null
    }
  }

  function load(item: PracticeItem): Promise<Loaded | null> {
    const key = keyOf(item)
    let promise = loaded.get(key)
    if (!promise) {
      promise = fetchItem(item)
      promise.catch(() => loaded.delete(key))
      loaded.set(key, promise)
    }
    return promise
  }

  const { data, status } = useAsyncData(
    () => `practice-item-${toValue(item) ? keyOf(toValue(item)!) : 'none'}`,
    async () => {
      const current = toValue(item)
      const upcoming = toValue(next)
      if (upcoming) load(upcoming).catch(() => {})
      return { key: current ? keyOf(current) : null, value: current ? await load(current) : null }
    },
    { watch: [() => toValue(item)] },
  )

  const currentKey = () => {
    const current = toValue(item)
    return current ? keyOf(current) : null
  }
  const fresh = computed(() => data.value?.key === currentKey())
  const loading = computed(() => (fresh.value ? status.value : status.value === 'error' ? 'error' : 'pending'))

  const text = computed<PracticeText | null>(() => {
    const value = fresh.value ? data.value?.value : null
    if (!value) return null
    if (value.kind === 'kanji') {
      const { kanji } = value
      const readings = [...kanji.kun_readings, ...kanji.on_readings].filter(r => r.enabled).map(r => r.text)
      return {
        text: kanji.literal,
        reading: readings.slice(0, MEANINGS).join('・') || undefined,
        meanings: kanjiMeanings(kanji, lang.value).slice(0, MEANINGS),
      }
    }
    if (value.kind === 'entry') {
      const writing = entryWriting(value.entry)
      return writing && { ...writing, meanings: entryMeanings(value.entry, glossCode.value).slice(0, MEANINGS) }
    }
    return { text: value.text, meanings: value.meanings.filter(m => m.lang === lang.value).map(m => m.text).slice(0, MEANINGS) }
  })

  return { text, status: loading }
}
