<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import type { ItemKind, LibraryQuery } from '~/models/practice'
import { listLibraryEntries, listLibraryKanji } from '~/services/library'

// The user's library: words and kanji in tabs, newest first. Tab, filter and
// page live in the URL so the back button returns to the same view.

const PAGE_SIZE = 24

const route = useRoute()
const router = useRouter()
const api = useApi()

const tab = computed<ItemKind>({
  get: () => (route.query.tab === 'kanji' ? 'kanji' : 'entries'),
  set: value => router.replace({ query: { tab: value } }),
})
const { filter, active, options: filters } = useActiveFilter()
const page = computed<number>({
  get: () => Math.max(1, Number(route.query.page) || 1),
  set: value => router.push({ query: { ...route.query, page: value } }),
})

const tabs: TabsItem[] = [
  { label: 'Palabras', value: 'entries', icon: 'i-lucide-languages' },
  { label: 'Kanji', value: 'kanji', icon: 'i-lucide-type' },
]

const { data, status, error } = useAsyncData(
  'library',
  async () => {
    const query: LibraryQuery = {
      limit: PAGE_SIZE,
      offset: (page.value - 1) * PAGE_SIZE,
      active: active.value,
    }
    return tab.value === 'entries'
      ? { kind: 'entries' as const, page: await listLibraryEntries(api, query) }
      : { kind: 'kanji' as const, page: await listLibraryKanji(api, query) }
  },
  { watch: [tab, filter, page] },
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
        <USelect v-model="filter" :items="filters" class="w-36" aria-label="Filtrar por estado" />
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
        v-else-if="data && !data.page.items.length"
        icon="i-lucide-library-big"
        :title="filter === 'all' ? (tab === 'entries' ? 'Aún no tienes palabras' : 'Aún no tienes kanji') : 'Nada con este filtro'"
        :description="filter === 'all' ? 'Búscalas en el diccionario e impórtalas.' : undefined"
        :actions="filter === 'all' ? [{ label: 'Ir al diccionario', to: '/dictionary', icon: 'i-lucide-book-open' }] : undefined"
      />

      <template v-else-if="data">
        <p class="text-sm text-muted">{{ data.page.total }} en total</p>
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
