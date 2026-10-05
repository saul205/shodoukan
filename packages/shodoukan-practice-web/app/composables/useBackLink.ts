import type { ItemKind } from '~/models/practice'
import { safeReturnPath } from '~/utils/return-path'

// The pages that open an item's library page with `?from=<their path>`, and
// how its back button names them.
const RETURNS: [prefix: string, label: string][] = [
  ['/exercise-sessions/', 'Volver a la sesión'],
  ['/exercises/', 'Volver al ejercicio'],
  ['/statistics', 'Volver a las estadísticas'],
]

/**
 * Where the library detail page goes back to: the page it was opened from
 * (`?from=<path>`: a session, which picks up where it was, with its review
 * filter; an exercise; the statistics), the collection (`?collection=<id>`),
 * or the library. `from` is only taken for those pages.
 */
export function useBackLink(kind: ItemKind) {
  const route = useRoute()
  return computed(() => {
    const from = typeof route.query.from === 'string' ? safeReturnPath(route.query.from) : '/'
    const known = RETURNS.find(([prefix]) => from.startsWith(prefix))
    if (known) return { to: from, label: known[1] }
    const collection = Number(route.query.collection)
    if (Number.isInteger(collection) && collection > 0)
      return { to: `/collections/${kind}/${collection}`, label: 'Volver a la colección' }
    return { to: { path: '/library', query: kind === 'kanji' ? { tab: 'kanji' } : {} }, label: 'Volver a la librería' }
  })
}
