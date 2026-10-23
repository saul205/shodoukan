import type { Collection, ItemKind } from '~/models/practice'
import { addToCollection, createCollection, listCollections, removeFromCollection } from '~/services/collections'
import { getEntryCollections, getKanjiCollections } from '~/services/library'
import { apiStatus } from '~/utils/api-error'

/**
 * The collections (tags) a library item is in, and all the user's collections
 * of that kind, with adding, removing and creating. Nothing is fetched until
 * `load()`. Without an `itemId` (not imported yet) the item is in none.
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

  /**
   * Create an empty collection of this kind (no description; that's edited on
   * the collections page). Returns it, or null if it couldn't be created.
   */
  async function create(name: string): Promise<Collection | null> {
    busy.value = true
    try {
      const created = await createCollection(api, toValue(kind), { name: name.trim(), description: null })
      await load()
      return created
    }
    catch (error) {
      const status = apiStatus(error)
      if (status === 409) notify.failure(error, 'Ya tienes una colección con ese nombre')
      else if (status === 422) notify.failure(error, 'El nombre debe tener entre 1 y 100 caracteres')
      else notify.failure(error, 'No se ha podido crear la colección')
      return null
    }
    finally {
      busy.value = false
    }
  }

  return { all, mine, busy, has, load, add, remove, create }
}
