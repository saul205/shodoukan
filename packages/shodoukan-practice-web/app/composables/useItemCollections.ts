import type { Collection, ItemKind } from '~/models/practice'
import { addToCollection, listCollections, removeFromCollection } from '~/services/collections'
import { getEntryCollections, getKanjiCollections } from '~/services/library'

/**
 * The collections (tags) a library item is in, and all the user's collections
 * of that kind, with adding and removing. Nothing is fetched until `load()`.
 * Without an `itemId` (not imported yet) the item is in none.
 */
export function useItemCollections(
  kind: MaybeRefOrGetter<ItemKind>,
  itemId: MaybeRefOrGetter<number | undefined>,
) {
  const api = useApi()
  const notify = useNotify()

  /** The user's collections of this kind; null until loaded. */
  const all = ref<Collection[] | null>(null)
  /** The ones the item is in. */
  const mine = ref<Collection[]>([])
  const busy = ref(false)

  const has = (collection: Collection) => mine.value.some(c => c.id === collection.id)

  async function load() {
    const k = toValue(kind)
    const id = toValue(itemId)
    try {
      const [inside, every] = await Promise.all([
        id === undefined
          ? []
          : k === 'entries' ? getEntryCollections(api, id) : getKanjiCollections(api, id),
        listCollections(api, k),
      ])
      mine.value = inside
      all.value = every
    }
    catch (error) {
      notify.failure(error)
    }
  }

  async function run(action: (id: number) => Promise<void>) {
    const id = toValue(itemId)
    if (id === undefined) return
    busy.value = true
    try {
      await action(id)
      await load()
    }
    catch (error) {
      notify.failure(error)
    }
    finally {
      busy.value = false
    }
  }

  const add = (collection: Collection) =>
    run(id => addToCollection(api, toValue(kind), collection.id, id))
  const remove = (collection: Collection) =>
    run(id => removeFromCollection(api, toValue(kind), collection.id, id))

  return { all, mine, busy, has, load, add, remove }
}
