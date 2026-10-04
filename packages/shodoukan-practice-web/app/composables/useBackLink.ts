import type { ItemKind } from '~/models/practice'

/**
 * Where the library detail page goes back to: the collection it was opened
 * from (`?collection=<id>`), or the library.
 */
export function useBackLink(kind: ItemKind) {
  const route = useRoute()
  return computed(() => {
    const collection = Number(route.query.collection)
    if (Number.isInteger(collection) && collection > 0)
      return { to: `/collections/${kind}/${collection}`, label: 'Volver a la colección' }
    return { to: { path: '/library', query: kind === 'kanji' ? { tab: 'kanji' } : {} }, label: 'Volver a la librería' }
  })
}
