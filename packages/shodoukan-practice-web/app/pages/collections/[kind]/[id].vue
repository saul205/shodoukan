<script setup lang="ts">
import CollectionFormModal from '~/components/CollectionFormModal.vue'
import ConfirmModal from '~/components/ConfirmModal.vue'
import LibraryPickerModal from '~/components/LibraryPickerModal.vue'
import type { ItemKind } from '~/models/practice'
import {
  deleteCollection,
  getCollection,
  listCollectionEntries,
  listCollectionKanji,
  removeFromCollection,
} from '~/services/collections'

// One collection and its items, inactive ones included unless filtered out (as
// in the library). Items open the library's detail page, which links back here.

definePageMeta({
  validate: route => ['entries', 'kanji'].includes(String(route.params.kind)),
})

const PAGE_SIZE = 24

const route = useRoute()
const router = useRouter()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()

const kind = computed(() => route.params.kind as ItemKind)
const id = computed(() => Number(route.params.id))
const { filter, active, options: filters } = useActiveFilter()
const page = computed<number>({
  get: () => Math.max(1, Number(route.query.page) || 1),
  set: value => router.push({ query: { ...route.query, page: value } }),
})

const { data: collection, error: collectionError, refresh: refreshCollection } = useAsyncData(
  () => `collection-${kind.value}-${id.value}`,
  () => getCollection(api, kind.value, id.value),
  { watch: [kind, id] },
)

const { data: items, status, refresh: refreshItems } = useAsyncData(
  () => `collection-items-${kind.value}-${id.value}-${filter.value}-${page.value}`,
  async () => {
    const query = { limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE, active: active.value }
    return kind.value === 'entries'
      ? { kind: 'entries' as const, page: await listCollectionEntries(api, id.value, query) }
      : { kind: 'kanji' as const, page: await listCollectionKanji(api, id.value, query) }
  },
  { watch: [kind, id, filter, page] },
)

const countLabel = computed(() => {
  const total = items.value?.page.total ?? 0
  if (filter.value === 'active') return `${total} activos`
  if (filter.value === 'inactive') return `${total} inactivos`
  return total === 1 ? '1 elemento' : `${total} elementos`
})

const backToLibrary = computed(() => ({ path: '/collections', query: kind.value === 'kanji' ? { tab: 'kanji' } : {} }))

async function addItems() {
  if (!collection.value) return
  const added = await overlay.create(LibraryPickerModal).open({
    kind: kind.value,
    collectionId: id.value,
    collectionName: collection.value.name,
  }).result
  if (added) {
    notify.success(added === 1 ? 'Añadido a la colección' : `${added} añadidos a la colección`)
    await refreshItems()
  }
}

async function removeItem(itemId: number) {
  try {
    await removeFromCollection(api, kind.value, id.value, itemId)
    await refreshItems()
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido quitar')
  }
}

async function edit() {
  if (!collection.value) return
  const saved = await overlay.create(CollectionFormModal).open({ kind: kind.value, collection: collection.value }).result
  if (saved) await refreshCollection()
}

async function remove() {
  if (!collection.value) return
  const confirmed = await overlay.create(ConfirmModal).open({
    title: `¿Eliminar «${collection.value.name}»?`,
    description: 'Sus elementos siguen en tu librería; solo desaparece la colección.',
  }).result
  if (!confirmed) return
  try {
    await deleteCollection(api, kind.value, id.value)
    notify.success('Colección eliminada')
    await navigateTo(backToLibrary.value)
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido eliminar')
  }
}
</script>

<template>
  <AppPanel :title="collection?.name ?? 'Colección'">
    <template #leading>
      <UButton :to="backToLibrary" icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver a mis colecciones" />
    </template>
    <template v-if="collection" #actions>
      <UButton label="Añadir" icon="i-lucide-plus" @click="addItems" />
      <UDropdownMenu
        :items="[
          [{ label: 'Editar', icon: 'i-lucide-pencil', onSelect: edit }],
          [{ label: 'Eliminar colección', icon: 'i-lucide-trash-2', color: 'error', onSelect: remove }],
        ]"
        :content="{ align: 'end' }"
      >
        <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" aria-label="Acciones" />
      </UDropdownMenu>
    </template>

    <UEmpty
      v-if="collectionError"
      icon="i-lucide-search-x"
      title="No se ha encontrado esta colección"
      :actions="[{ label: 'Volver a mis colecciones', to: backToLibrary, icon: 'i-lucide-arrow-left' }]"
    />

    <div v-else class="space-y-5">
      <div v-if="collection" class="flex flex-wrap items-start justify-between gap-3">
        <div class="space-y-1">
          <p class="text-sm text-muted">
            Colección de {{ kind === 'entries' ? 'palabras' : 'kanji' }}<template v-if="items"> · {{ countLabel }}</template>
          </p>
          <p v-if="collection.description" class="text-toned">{{ collection.description }}</p>
        </div>
        <USelect v-model="filter" :items="filters" class="w-36" aria-label="Filtrar por estado" />
      </div>

      <div v-if="status === 'pending' && !items" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <USkeleton v-for="i in 6" :key="i" class="h-32" />
      </div>

      <UEmpty
        v-else-if="items && !items.page.items.length && filter !== 'all'"
        icon="i-lucide-filter-x"
        title="Nada con este filtro"
      />

      <UEmpty
        v-else-if="items && !items.page.items.length"
        icon="i-lucide-folder-open"
        title="Esta colección está vacía"
        description="Añade elementos de tu librería."
        :actions="[{ label: 'Añadir elementos', icon: 'i-lucide-plus', onClick: addItems }]"
      />

      <template v-else-if="items">
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <template v-if="items.kind === 'entries'">
            <LibraryEntryCard
              v-for="entry in items.page.items"
              :key="entry.id"
              :entry="entry"
              :to="{ path: `/library/entries/${entry.id}`, query: { collection: id } }"
            >
              <template #actions>
                <UButton
                  icon="i-lucide-folder-minus"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  aria-label="Quitar de la colección"
                  @click="removeItem(entry.id)"
                />
              </template>
            </LibraryEntryCard>
          </template>
          <template v-else>
            <LibraryKanjiCard
              v-for="k in items.page.items"
              :key="k.id"
              :kanji="k"
              :to="{ path: `/library/kanji/${k.id}`, query: { collection: id } }"
            >
              <template #actions>
                <UButton
                  icon="i-lucide-folder-minus"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  aria-label="Quitar de la colección"
                  @click="removeItem(k.id)"
                />
              </template>
            </LibraryKanjiCard>
          </template>
        </div>
        <UPagination
          v-if="items.page.total > PAGE_SIZE"
          v-model:page="page"
          :total="items.page.total"
          :items-per-page="PAGE_SIZE"
          class="flex justify-center"
        />
      </template>
    </div>
  </AppPanel>
</template>
