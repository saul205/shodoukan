import { getImportStatus, importEntry, importKanji } from '~/services/library'

/**
 * Which dictionary results are in the user's library, and importing the
 * rest. Ask with `refresh(entryIds, literals)` whenever the results change.
 */
export function useImportStatus() {
  const api = useApi()
  const notify = useNotify()

  /** Dictionary entry id → practice entry id. */
  const entries = ref(new Map<number, number>())
  /** Kanji literal → practice kanji id. */
  const kanji = ref(new Map<string, number>())
  const importing = ref(new Set<string>())

  async function refresh(entryIds: number[], literals: string[]) {
    try {
      const status = await getImportStatus(api, entryIds, literals)
      entries.value = new Map(status.entries.map(e => [e.source_entry_id, e.id]))
      kanji.value = new Map(status.kanji.map(k => [k.literal, k.id]))
    }
    catch {
      // Without status every result shows "Importar"; importing again is harmless.
    }
  }

  async function addEntry(entryId: number) {
    const key = `entry:${entryId}`
    importing.value = new Set(importing.value).add(key)
    try {
      const copy = await importEntry(api, entryId)
      entries.value = new Map(entries.value).set(entryId, copy.id)
      notify.success('Añadida a tu librería')
    }
    catch (error) {
      notify.failure(error, 'No se ha podido importar')
    }
    finally {
      const next = new Set(importing.value)
      next.delete(key)
      importing.value = next
    }
  }

  async function addKanji(literal: string) {
    const key = `kanji:${literal}`
    importing.value = new Set(importing.value).add(key)
    try {
      const copy = await importKanji(api, literal)
      kanji.value = new Map(kanji.value).set(literal, copy.id)
      notify.success('Añadido a tu librería')
    }
    catch (error) {
      notify.failure(error, 'No se ha podido importar')
    }
    finally {
      const next = new Set(importing.value)
      next.delete(key)
      importing.value = next
    }
  }

  const isImportingEntry = (entryId: number) => importing.value.has(`entry:${entryId}`)
  const isImportingKanji = (literal: string) => importing.value.has(`kanji:${literal}`)

  return { entries, kanji, refresh, addEntry, addKanji, isImportingEntry, isImportingKanji }
}
