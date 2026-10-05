import { SUPPORTED_LANGUAGES, glossLang } from 'shodoukan-ui'
import type { ItemKind } from '~/models/practice'

const STORAGE_KEY = 'shodoukan:meaning-lang'

/**
 * The language meanings are shown and added in (ISO 639-1, e.g. "en").
 * Shared by every screen and remembered in this browser.
 */
export function useMeaningLang() {
  const lang = useState<string>('meaning-lang', () => readStored() ?? 'en')

  watch(lang, (value) => {
    try {
      localStorage.setItem(STORAGE_KEY, value)
    }
    catch {
      // Storage can be unavailable (private mode); the choice just isn't kept.
    }
  })

  /** The same language as entry glosses store it (ISO 639-2, e.g. "eng"). */
  const glossCode = computed(() => glossLang(lang.value))

  const options = SUPPORTED_LANGUAGES.map(l => ({ label: l.label, value: l.code }))

  /** The language as items of a kind store it: "eng" for words, "en" for kanji. */
  function codeFor(kind: ItemKind): string {
    return kind === 'entries' ? glossCode.value : lang.value
  }

  return { lang, glossCode, options, codeFor }
}

function readStored(): string | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return SUPPORTED_LANGUAGES.some(l => l.code === stored) ? stored : null
  }
  catch {
    return null
  }
}
