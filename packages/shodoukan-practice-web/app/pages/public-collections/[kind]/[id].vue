<script setup lang="ts">
import type { ItemKind } from '~/models/practice'
import {
  getPublicCollection,
  importPublicCollection,
  previewPublicEntries,
  previewPublicKanji,
} from '~/services/public-collections'
import { importSummary } from '~/utils/collection-file'

// A public collection: who shares it and its counts, a preview of its
// published version (each item as importing it would give it, not stored, so
// not linked), and importing it into the user's library as a new collection.

definePageMeta({
  validate: route => ['entries', 'kanji'].includes(String(route.params.kind)),
})

const PAGE_SIZE = 24

const route = useRoute()
const router = useRouter()
const api = useApi()
const notify = useNotify()

const kind = computed(() => route.params.kind as ItemKind)
const id = computed(() => Number(route.params.id))
const page = computed<number>({
  get: () => Math.max(1, Number(route.query.page) || 1),
  set: value => router.push({ query: { ...route.query, page: value } }),
})
const back = computed(() => ({ path: '/public-collections', query: kind.value === 'kanji' ? { tab: 'kanji' } : {} }))

const { data: collection, error, refresh } = useAsyncData(
  () => `public-collection-${kind.value}-${id.value}`,
  () => getPublicCollection(api, kind.value, id.value),
  { watch: [kind, id] },
)

const { data: preview, status } = useAsyncData(
  () => `public-collection-items-${kind.value}-${id.value}`,
  async () => {
    const query = { limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE }
    return kind.value === 'entries'
      ? { kind: 'entries' as const, page: await previewPublicEntries(api, id.value, query) }
      : { kind: 'kanji' as const, page: await previewPublicKanji(api, id.value, query) }
  },
  { watch: [kind, id, page] },
)

const importing = ref(false)

async function importIt() {
  importing.value = true
  try {
    const result = await importPublicCollection(api, kind.value, id.value)
    notify.success(`Importada como «${result.collection.name}»`, importSummary(result))
    await refresh()
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido importar')
  }
  finally {
    importing.value = false
  }
}

function date(iso: string) {
  return new Date(iso).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })
}
</script>

<template>
  <AppPanel :title="collection?.name ?? 'Colección pública'">
    <template #leading>
      <UButton :to="back" icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver a colecciones públicas" />
    </template>
    <template v-if="collection" #actions>
      <UButton
        v-if="collection.is_mine"
        :to="`/collections/${kind}/${collection.id}`"
        label="Gestionar"
        icon="i-lucide-folder-cog"
        color="neutral"
        variant="outline"
      />
      <UButton
        v-else
        :label="collection.imported_version ? 'Importar otra vez' : 'Importar a mi librería'"
        icon="i-lucide-download"
        :loading="importing"
        data-testid="import-public"
        @click="importIt"
      />
    </template>

    <UEmpty
      v-if="error"
      icon="i-lucide-search-x"
      title="Esta colección no existe o ya no es pública"
      :actions="[{ label: 'Volver a colecciones públicas', to: back, icon: 'i-lucide-arrow-left' }]"
    />

    <div v-else class="space-y-5">
      <div v-if="collection" class="space-y-2">
        <p class="text-sm text-muted">
          Colección de {{ kind === 'entries' ? 'palabras' : 'kanji' }}
          {{ collection.is_mine ? '(tuya)' : `de ${collection.owner}` }}
          · versión {{ collection.version }}, {{ date(collection.published_at) }}
          · {{ collection.item_count }} elementos
          · {{ collection.downloads === 1 ? '1 descarga' : `${collection.downloads} descargas` }}
        </p>
        <p v-if="collection.description" class="text-toned">{{ collection.description }}</p>
        <UAlert
          v-if="collection.imported_version"
          icon="i-lucide-check"
          color="success"
          variant="soft"
          :title="`Ya la importaste (versión ${collection.imported_version})`"
          description="Importarla otra vez crea otra colección; lo que ya tienes no se duplica."
        />
      </div>

      <div v-if="status === 'pending' && !preview" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <USkeleton v-for="i in 6" :key="i" class="h-32" />
      </div>

      <template v-else-if="preview">
        <p class="text-sm text-muted">Así quedarán en tu librería al importarla.</p>
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <template v-if="preview.kind === 'entries'">
            <LibraryEntryCard v-for="entry in preview.page.items" :key="entry.id" :entry="entry" />
          </template>
          <template v-else>
            <LibraryKanjiCard v-for="k in preview.page.items" :key="k.id" :kanji="k" />
          </template>
        </div>
        <UPagination
          v-if="preview.page.total > PAGE_SIZE"
          v-model:page="page"
          :total="preview.page.total"
          :items-per-page="PAGE_SIZE"
          class="flex justify-center"
        />
      </template>
    </div>
  </AppPanel>
</template>
