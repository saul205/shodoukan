<script setup lang="ts">
import type { DropdownMenuItem, TabsItem } from '@nuxt/ui'
import CollectionFormModal from '~/components/CollectionFormModal.vue'
import ConfirmModal from '~/components/ConfirmModal.vue'
import PublishCollectionModal from '~/components/PublishCollectionModal.vue'
import type { Collection, ItemKind } from '~/models/practice'
import {
  deleteCollection,
  exportCollection,
  importCollection,
  listCollections,
  unpublishCollection,
} from '~/services/collections'
import { apiStatus } from '~/utils/api-error'
import { downloadCollectionFile, importSummary, parseCollectionFile } from '~/utils/collection-file'

// "Mis colecciones": word and kanji collections in tabs; create, edit and
// delete them, open one to see its items, export one to a file or import
// one from a file (into a new collection), and publish one for others.

const route = useRoute()
const router = useRouter()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()
const toast = useToast()

const kind = computed<ItemKind>({
  get: () => (route.query.tab === 'kanji' ? 'kanji' : 'entries'),
  set: value => router.replace({ query: { tab: value } }),
})

const tabs: TabsItem[] = [
  { label: 'Palabras', value: 'entries', icon: 'i-lucide-languages' },
  { label: 'Kanji', value: 'kanji', icon: 'i-lucide-type' },
]

const { data: collections, status, error, refresh } = useAsyncData(
  'collections',
  () => listCollections(api, kind.value),
  { watch: [kind] },
)

const form = overlay.create(CollectionFormModal)
const confirm = overlay.create(ConfirmModal)
const publisher = overlay.create(PublishCollectionModal)

async function create() {
  const saved = await form.open({ kind: kind.value }).result
  if (saved) {
    notify.success(`Colección «${saved.name}» creada`)
    await refresh()
  }
}

async function edit(collection: Collection) {
  const saved = await form.open({ kind: kind.value, collection }).result
  if (saved) await refresh()
}

async function remove(collection: Collection) {
  const confirmed = await confirm.open({
    title: `¿Eliminar «${collection.name}»?`,
    description: 'Sus elementos siguen en tu librería; solo desaparece la colección.',
  }).result
  if (!confirmed) return
  try {
    await deleteCollection(api, kind.value, collection.id)
    notify.success('Colección eliminada')
    await refresh()
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido eliminar')
  }
}

async function exportToFile(collection: Collection) {
  try {
    downloadCollectionFile(await exportCollection(api, kind.value, collection.id))
  }
  catch (failure) {
    // The API refuses (422) only a collection too big to import back.
    const tooBig = apiStatus(failure) === 422
    notify.failure(failure, 'No se ha podido exportar', tooBig ? 'La colección tiene demasiados elementos para exportarla.' : undefined)
  }
}

const fileInput = ref<HTMLInputElement>()
const importing = ref(false)

async function importFromFile(event: Event) {
  const input = event.target as HTMLInputElement
  const chosen = input.files?.[0]
  input.value = '' // so choosing the same file again imports it again
  if (!chosen) return
  let file
  try {
    file = parseCollectionFile(await chosen.text())
  }
  catch (failure) {
    const description = failure instanceof Error ? failure.message : undefined
    toast.add({ title: 'No se puede importar', description, color: 'error', icon: 'i-lucide-circle-alert' })
    return
  }
  importing.value = true
  try {
    const result = await importCollection(api, file)
    notify.success(`Colección «${result.collection.name}» importada`, importSummary(result))
    if (file.kind !== kind.value) kind.value = file.kind // the watch reloads
    else await refresh()
  }
  catch (failure) {
    // 422: the API rejected the file's content; anything else isn't the file's fault.
    const invalid = apiStatus(failure) === 422
    notify.failure(failure, 'No se ha podido importar', invalid ? 'El archivo no es válido o está dañado; no se ha importado nada.' : undefined)
  }
  finally {
    importing.value = false
  }
}

async function publish(collection: Collection) {
  const published = await publisher.open({ kind: kind.value, collection }).result
  if (published) {
    notify.success(`«${published.name}» publicada (versión ${published.published_version})`)
    await refresh()
  }
}

async function unpublish(collection: Collection) {
  const confirmed = await confirm.open({
    title: `¿Dejar de publicar «${collection.name}»?`,
    description: 'Nadie más podrá verla ni importarla. Quien ya la importó conserva su copia.',
  }).result
  if (!confirmed) return
  try {
    await unpublishCollection(api, kind.value, collection.id)
    notify.success('Ya no es pública')
    await refresh()
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido dejar de publicar')
  }
}

function sharing(collection: Collection): DropdownMenuItem[] {
  if (!collection.is_public)
    return [{ label: 'Publicar', icon: 'i-lucide-globe', onSelect: () => publish(collection) }]
  return [
    { label: 'Publicar nueva versión', icon: 'i-lucide-globe', onSelect: () => publish(collection) },
    {
      label: 'Ver en colecciones públicas',
      icon: 'i-lucide-external-link',
      to: `/public-collections/${kind.value}/${collection.id}`,
    },
    { label: 'Dejar de publicar', icon: 'i-lucide-globe-lock', onSelect: () => unpublish(collection) },
  ]
}

function actions(collection: Collection): DropdownMenuItem[][] {
  return [
    [
      { label: 'Editar', icon: 'i-lucide-pencil', onSelect: () => edit(collection) },
      { label: 'Exportar', icon: 'i-lucide-download', onSelect: () => exportToFile(collection) },
    ],
    sharing(collection),
    [{ label: 'Eliminar', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => remove(collection) }],
  ]
}
</script>

<template>
  <AppPanel title="Mis colecciones">
    <template #actions>
      <input
        ref="fileInput"
        type="file"
        accept=".json,application/json"
        class="hidden"
        data-testid="import-file"
        @change="importFromFile"
      >
      <UButton
        label="Importar"
        icon="i-lucide-upload"
        color="neutral"
        variant="outline"
        :loading="importing"
        @click="fileInput?.click()"
      />
      <UButton label="Nueva colección" icon="i-lucide-plus" @click="create" />
    </template>

    <div class="space-y-5">
      <UTabs v-model="kind" :items="tabs" :content="false" />

      <div v-if="status === 'pending' && !collections" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <USkeleton v-for="i in 3" :key="i" class="h-24" />
      </div>

      <UAlert
        v-else-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="No se han podido cargar tus colecciones"
      />

      <UEmpty
        v-else-if="!collections?.length"
        icon="i-lucide-folders"
        :title="kind === 'entries' ? 'Aún no tienes colecciones de palabras' : 'Aún no tienes colecciones de kanji'"
        description="Agrupa elementos de tu librería para estudiarlos juntos: verbos, JLPT N5, cocina…"
        :actions="[{ label: 'Nueva colección', icon: 'i-lucide-plus', onClick: create }]"
      />

      <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <UCard v-for="collection in collections" :key="collection.id" :ui="{ body: 'p-4 sm:p-4 flex items-start gap-3' }">
          <NuxtLink :to="`/collections/${kind}/${collection.id}`" class="min-w-0 flex-1">
            <p class="flex items-center gap-2">
              <span class="truncate font-medium text-highlighted">{{ collection.name }}</span>
              <UBadge
                v-if="collection.is_public"
                :label="`Pública · v${collection.published_version}`"
                icon="i-lucide-globe"
                color="success"
                variant="soft"
                size="sm"
                class="shrink-0"
              />
            </p>
            <p class="line-clamp-2 text-sm text-muted">{{ collection.description || 'Sin descripción' }}</p>
          </NuxtLink>
          <UDropdownMenu :items="actions(collection)" :content="{ align: 'end' }">
            <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" size="sm" aria-label="Acciones" />
          </UDropdownMenu>
        </UCard>
      </div>
    </div>
  </AppPanel>
</template>
