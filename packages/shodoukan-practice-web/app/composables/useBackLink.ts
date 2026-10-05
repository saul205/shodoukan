import type { ItemKind } from '~/models/practice'
import { safeReturnPath } from '~/utils/return-path'

/**
 * Where the library detail page goes back to: the exercise session it was
 * opened from (`?from=<the session page's path>`, with its review filter;
 * the session picks up where it was), the collection (`?collection=<id>`),
 * or the library.
 */
export function useBackLink(kind: ItemKind) {
  const route = useRoute()
  return computed(() => {
    const from = typeof route.query.from === 'string' ? safeReturnPath(route.query.from) : '/'
    if (from.startsWith('/exercise-sessions/'))
      return { to: from, label: 'Volver a la sesión' }
    const collection = Number(route.query.collection)
    if (Number.isInteger(collection) && collection > 0)
      return { to: `/collections/${kind}/${collection}`, label: 'Volver a la colección' }
    return { to: { path: '/library', query: kind === 'kanji' ? { tab: 'kanji' } : {} }, label: 'Volver a la librería' }
  })
}
