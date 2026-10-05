import type { ItemKind } from '~/models/practice'

/**
 * Where the library detail page goes back to: the exercise session it was
 * opened from (`?session=<id>`, which picks up where it was), the collection
 * (`?collection=<id>`), or the library.
 */
export function useBackLink(kind: ItemKind) {
  const route = useRoute()
  return computed(() => {
    const session = Number(route.query.session)
    if (Number.isInteger(session) && session > 0)
      return { to: `/exercise-sessions/${session}`, label: 'Volver a la sesión' }
    const collection = Number(route.query.collection)
    if (Number.isInteger(collection) && collection > 0)
      return { to: `/collections/${kind}/${collection}`, label: 'Volver a la colección' }
    return { to: { path: '/library', query: kind === 'kanji' ? { tab: 'kanji' } : {} }, label: 'Volver a la librería' }
  })
}
