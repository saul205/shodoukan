<script setup lang="ts">
import type { DropdownMenuItem, TabsItem } from '@nuxt/ui'
import CollectionFormModal from '~/components/CollectionFormModal.vue'
import ConfirmModal from '~/components/ConfirmModal.vue'
import type { Collection, ItemKind } from '~/models/practice'
import { deleteCollection, listCollections } from '~/services/collections'

// "Mis colecciones": word and kanji collections in tabs; create, edit and
// delete them, and open one to see its items.

const route = useRoute()
const router = useRouter()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()

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

function actions(collection: Collection): DropdownMenuItem[][] {
  return [
    [{ label: 'Editar', icon: 'i-lucide-pencil', onSelect: () => edit(collection) }],
    [{ label: 'Eliminar', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => remove(collection) }],
  ]
}
</script>

<template>
  <AppPanel title="Mis colecciones">
    <template #actions>
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
            <p class="truncate font-medium text-highlighted">{{ collection.name }}</p>
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
