<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import type { ItemKind, LibraryQuery } from '~/models/practice'
import { listLibraryEntries, listLibraryKanji } from '~/services/library'

// The user's library: words and kanji in tabs, newest first, with a search
// (best match first). Tab, search, filter and page live in the URL so the back
// button returns to the same view.

const PAGE_SIZE = 24

const route = useRoute()
const router = useRouter()
const api = useApi()
const { lang, glossCode } = useMeaningLang()

type ActiveFilter = 'all' | 'active' | 'inactive'

const tab = computed<ItemKind>({
  get: () => (route.query.tab === 'kanji' ? 'kanji' : 'entries'),
  // The search is kept: the same word can be looked for among kanji.
  set: value => router.replace({ query: { tab: value, q: route.query.q } }),
})
const search = computed<string>({
  get: () => (typeof route.query.q === 'string' ? route.query.q : ''),
  set: value => router.replace({ query: { ...route.query, q: value || undefined, page: undefined } }),
})
const filter = computed<ActiveFilter>({
  get: () => (['active', 'inactive'].includes(String(route.query.active)) ? route.query.active as ActiveFilter : 'all'),
  set: value => router.replace({ query: { ...route.query, active: value === 'all' ? undefined : value, page: undefined } }),
})
const page = computed<number>({
  get: () => Math.max(1, Number(route.query.page) || 1),
  set: value => router.push({ query: { ...route.query, page: value } }),
})

const tabs: TabsItem[] = [
  { label: 'Palabras', value: 'entries', icon: 'i-lucide-languages' },
  { label: 'Kanji', value: 'kanji', icon: 'i-lucide-type' },
]
const filters = [
  { label: 'Todos', value: 'all' },
  { label: 'Activos', value: 'active' },
  { label: 'Inactivos', value: 'inactive' },
]

const { data, status, error } = useAsyncData(
  'library',
  async () => {
    const query: LibraryQuery = {
      limit: PAGE_SIZE,
      offset: (page.value - 1) * PAGE_SIZE,
      active: filter.value === 'all' ? undefined : filter.value === 'active',
      q: search.value || undefined,
      // Meanings are searched in the language they're shown in.
      meaning_lang: search.value ? (tab.value === 'entries' ? glossCode.value : lang.value) : undefined,
    }
    return tab.value === 'entries'
      ? { kind: 'entries' as const, page: await listLibraryEntries(api, query) }
      : { kind: 'kanji' as const, page: await listLibraryKanji(api, query) }
  },
  { watch: [tab, search, filter, page, lang] },
)
</script>

<template>
  <AppPanel title="Mi librería">
    <template #actions>
      <UButton label="Importar del diccionario" icon="i-lucide-book-open" to="/dictionary" variant="soft" />
    </template>

    <div class="space-y-5">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <UTabs v-model="tab" :items="tabs" :content="false" />
        <div class="flex flex-1 flex-wrap justify-end gap-3">
          <LibrarySearchInput v-model="search" class="min-w-56 flex-1 sm:max-w-sm" />
          <USelect v-model="filter" :items="filters" class="w-36" aria-label="Filtrar por estado" />
        </div>
      </div>

      <div v-if="status === 'pending' && !data" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <USkeleton v-for="i in 6" :key="i" class="h-32" />
      </div>

      <UAlert
        v-else-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="No se ha podido cargar tu librería"
      />

      <UEmpty
        v-else-if="data && !data.page.items.length && search"
        icon="i-lucide-search-x"
        :title="`Sin resultados para «${search}»`"
        description="Prueba con otra forma de escribirlo, en kana o romaji, o con un significado."
      />

      <UEmpty
        v-else-if="data && !data.page.items.length"
        icon="i-lucide-library-big"
        :title="filter === 'all' ? (tab === 'entries' ? 'Aún no tienes palabras' : 'Aún no tienes kanji') : 'Nada con este filtro'"
        :description="filter === 'all' ? 'Búscalas en el diccionario e impórtalas.' : undefined"
        :actions="filter === 'all' ? [{ label: 'Ir al diccionario', to: '/dictionary', icon: 'i-lucide-book-open' }] : undefined"
      />

      <template v-else-if="data">
        <p class="text-sm text-muted">{{ data.page.total }} {{ search ? 'encontrados' : 'en total' }}</p>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <template v-if="data.kind === 'entries'">
            <LibraryEntryCard
              v-for="entry in data.page.items"
              :key="entry.id"
              :entry="entry"
              :to="`/library/entries/${entry.id}`"
            />
          </template>
          <template v-else>
            <LibraryKanjiCard
              v-for="kanji in data.page.items"
              :key="kanji.id"
              :kanji="kanji"
              :to="`/library/kanji/${kanji.id}`"
            />
          </template>
        </div>
        <UPagination
          v-if="data.page.total > PAGE_SIZE"
          v-model:page="page"
          :total="data.page.total"
          :items-per-page="PAGE_SIZE"
          class="flex justify-center"
        />
      </template>
    </div>
  </AppPanel>
</template>
