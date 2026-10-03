import ConfirmModal from '~/components/ConfirmModal.vue'
import {
  getImportStatus,
  importEntry,
  importKanji,
  removeLibraryEntry,
  removeLibraryKanji,
} from '~/services/library'

/**
 * Which dictionary results are in the user's library, importing the rest and
 * removing imported ones. Ask with `refresh(entryIds, literals)` whenever the
 * results change.
 */
export function useImportStatus() {
  const api = useApi()
  const notify = useNotify()
  const overlay = useOverlay()

  /** Dictionary entry id → practice entry id. */
  const entries = ref(new Map<number, number>())
  /** Kanji literal → practice kanji id. */
  const kanji = ref(new Map<string, number>())
  /** Results being imported or removed, as `entry:<id>` / `kanji:<literal>`. */
  const busy = ref(new Set<string>())

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

  async function whileBusy(key: string, run: () => Promise<void>) {
    busy.value = new Set(busy.value).add(key)
    try {
      await run()
    }
    finally {
      const next = new Set(busy.value)
      next.delete(key)
      busy.value = next
    }
  }

  // Removing drops the user's notes and own meanings, as in the library pages.
  async function confirmRemoval(what: 'entry' | 'kanji'): Promise<boolean> {
    const again = what === 'entry' ? 'importarla' : 'importarlo'
    return await overlay.create(ConfirmModal).open({
      title: '¿Quitar de tu librería?',
      description: `Se borran tus notas y significados propios, y sale de todas tus colecciones. Podrás volver a ${again} desde el diccionario.`,
      confirmLabel: 'Quitar',
    }).result
  }

  async function addEntry(entryId: number) {
    await whileBusy(`entry:${entryId}`, async () => {
      try {
        const copy = await importEntry(api, entryId)
        entries.value = new Map(entries.value).set(entryId, copy.id)
        notify.success('Añadida a tu librería')
      }
      catch (error) {
        notify.failure(error, 'No se ha podido importar')
      }
    })
  }

  async function addKanji(literal: string) {
    await whileBusy(`kanji:${literal}`, async () => {
      try {
        const copy = await importKanji(api, literal)
        kanji.value = new Map(kanji.value).set(literal, copy.id)
        notify.success('Añadido a tu librería')
      }
      catch (error) {
        notify.failure(error, 'No se ha podido importar')
      }
    })
  }

  async function removeEntry(entryId: number) {
    const practiceId = entries.value.get(entryId)
    if (practiceId === undefined || !(await confirmRemoval('entry'))) return
    await whileBusy(`entry:${entryId}`, async () => {
      try {
        await removeLibraryEntry(api, practiceId)
        const next = new Map(entries.value)
        next.delete(entryId)
        entries.value = next
        notify.success('Quitada de tu librería')
      }
      catch (error) {
        notify.failure(error, 'No se ha podido quitar')
      }
    })
  }

  async function removeKanji(literal: string) {
    const practiceId = kanji.value.get(literal)
    if (practiceId === undefined || !(await confirmRemoval('kanji'))) return
    await whileBusy(`kanji:${literal}`, async () => {
      try {
        await removeLibraryKanji(api, practiceId)
        const next = new Map(kanji.value)
        next.delete(literal)
        kanji.value = next
        notify.success('Quitado de tu librería')
      }
      catch (error) {
        notify.failure(error, 'No se ha podido quitar')
      }
    })
  }

  const isBusyEntry = (entryId: number) => busy.value.has(`entry:${entryId}`)
  const isBusyKanji = (literal: string) => busy.value.has(`kanji:${literal}`)

  return {
    entries,
    kanji,
    refresh,
    addEntry,
    addKanji,
    removeEntry,
    removeKanji,
    isBusyEntry,
    isBusyKanji,
  }
}
