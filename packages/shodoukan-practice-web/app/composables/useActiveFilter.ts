export type ActiveFilter = 'all' | 'active' | 'inactive'

/**
 * The "Todos / Activos / Inactivos" filter of a list of library items, kept in
 * the URL (`?active=active|inactive`) so the back button returns to it.
 * Changing it goes back to the first page. `active` is what the API takes.
 */
export function useActiveFilter() {
  const route = useRoute()
  const router = useRouter()

  const filter = computed<ActiveFilter>({
    get: () => (['active', 'inactive'].includes(String(route.query.active)) ? route.query.active as ActiveFilter : 'all'),
    set: value => router.replace({ query: { ...route.query, active: value === 'all' ? undefined : value, page: undefined } }),
  })

  const active = computed(() => (filter.value === 'all' ? undefined : filter.value === 'active'))

  const options = [
    { label: 'Todos', value: 'all' },
    { label: 'Activos', value: 'active' },
    { label: 'Inactivos', value: 'inactive' },
  ]

  return { filter, active, options }
}
