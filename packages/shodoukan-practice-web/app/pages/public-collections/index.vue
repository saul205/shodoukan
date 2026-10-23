<script setup lang="ts">
import type { SelectItem, TabsItem } from '@nuxt/ui'
import type { ItemKind, PublicCollection, PublicOwner, PublicSort } from '~/models/practice'
import { searchPublicCollections } from '~/services/public-collections'

// "Colecciones públicas": what users share, words and kanji in tabs. Search by
// name, description or owner; show one's own, other people's or all; sort by
// downloads or date. Everything lives in the URL (?tab=&q=&owner=&sort=&page=).

const PAGE_SIZE = 24

const route = useRoute()
const router = useRouter()
const api = useApi()

function setQuery(changes: Record<string, string | number | undefined>) {
  router.replace({ query: { ...route.query, page: undefined, ...changes } })
}

const kind = computed<ItemKind>({
  get: () => (route.query.tab === 'kanji' ? 'kanji' : 'entries'),
  set: value => setQuery({ tab: value === 'kanji' ? 'kanji' : undefined }),
})
const search = computed<string>({
  get: () => (typeof route.query.q === 'string' ? route.query.q : ''),
  set: value => setQuery({ q: value || undefined }),
})
const owner = computed<PublicOwner>({
  get: () => (['mine', 'others'].includes(String(route.query.owner)) ? route.query.owner as PublicOwner : 'all'),
  set: value => setQuery({ owner: value === 'all' ? undefined : value }),
})
const sort = computed<PublicSort>({
  get: () => (route.query.sort === 'recent' ? 'recent' : 'popular'),
  set: value => setQuery({ sort: value === 'recent' ? 'recent' : undefined }),
})
const page = computed<number>({
  get: () => Math.max(1, Number(route.query.page) || 1),
  set: value => router.push({ query: { ...route.query, page: value } }),
})

const tabs: TabsItem[] = [
  { label: 'Palabras', value: 'entries', icon: 'i-lucide-languages' },
  { label: 'Kanji', value: 'kanji', icon: 'i-lucide-type' },
]
const owners: SelectItem[] = [
  { label: 'Todas', value: 'all' },
  { label: 'De otros', value: 'others' },
  { label: 'Mías', value: 'mine' },
]
const sorts: SelectItem[] = [
  { label: 'Más descargadas', value: 'popular' },
  { label: 'Más recientes', value: 'recent' },
]

const { data: collections, status, error } = useAsyncData(
  'public-collections',
  () => searchPublicCollections(api, kind.value, {
    q: search.value || undefined,
    owner: owner.value,
    sort: sort.value,
    limit: PAGE_SIZE,
    offset: (page.value - 1) * PAGE_SIZE,
  }),
  { watch: [kind, search, owner, sort, page] },
)

// "Importada (v1)", and the newer version when there is one.
function importedLabel(collection: PublicCollection) {
  const label = `Importada (v${collection.imported_version})`
  return collection.imported_version! < collection.version ? `${label} · v${collection.version} disponible` : label
}

function downloadsLabel(n: number) {
  return n === 1 ? '1 descarga' : `${n} descargas`
}
</script>

<template>
  <AppPanel title="Colecciones públicas">
    <div class="space-y-5">
      <UTabs v-model="kind" :items="tabs" :content="false" />

      <div class="flex flex-wrap gap-3">
        <LibrarySearchInput
          v-model="search"
          placeholder="Buscar por nombre, descripción o usuario"
          class="min-w-56 flex-1 sm:max-w-sm"
        />
        <USelect v-model="owner" :items="owners" class="w-32" aria-label="De quién" />
        <USelect v-model="sort" :items="sorts" class="w-44" aria-label="Ordenar" />
      </div>

      <div v-if="status === 'pending' && !collections" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <USkeleton v-for="i in 3" :key="i" class="h-32" />
      </div>

      <UAlert
        v-else-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="No se han podido cargar las colecciones públicas"
      />

      <UEmpty
        v-else-if="!collections?.items.length"
        icon="i-lucide-globe"
        :title="search ? `Sin resultados para «${search}»` : 'Aún no hay colecciones públicas aquí'"
        description="Publica una de tus colecciones desde «Mis colecciones» para compartirla."
        :actions="[{ label: 'Mis colecciones', icon: 'i-lucide-folders', to: '/collections' }]"
      />

      <template v-else>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <UCard
            v-for="collection in collections.items"
            :key="collection.id"
            class="transition hover:ring-accented"
            :ui="{ body: 'p-4 sm:p-4 h-full' }"
          >
            <NuxtLink
              :to="`/public-collections/${kind}/${collection.id}`"
              class="flex h-full flex-col gap-2"
              data-testid="public-collection"
            >
              <p class="truncate font-medium text-highlighted">{{ collection.name }}</p>
              <p class="line-clamp-2 flex-1 text-sm text-muted">{{ collection.description || 'Sin descripción' }}</p>
              <p class="text-xs text-muted">
                {{ collection.is_mine ? 'Tuya' : `de ${collection.owner}` }} · v{{ collection.version }}
                · {{ collection.item_count }} elementos · {{ downloadsLabel(collection.downloads) }}
              </p>
              <UBadge
                v-if="collection.imported_version"
                :label="importedLabel(collection)"
                :icon="collection.imported_version < collection.version ? 'i-lucide-sparkles' : 'i-lucide-check'"
                :color="collection.imported_version < collection.version ? 'primary' : 'success'"
                variant="soft"
                size="sm"
                class="self-start"
              />
            </NuxtLink>
          </UCard>
        </div>
        <UPagination
          v-if="collections.total > PAGE_SIZE"
          v-model:page="page"
          :total="collections.total"
          :items-per-page="PAGE_SIZE"
          class="flex justify-center"
        />
      </template>
    </div>
  </AppPanel>
</template>
