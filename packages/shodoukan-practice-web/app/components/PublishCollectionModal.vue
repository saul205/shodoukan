<script setup lang="ts">
import type { Collection, ItemKind } from '~/models/practice'
import { publishCollection } from '~/services/collections'

// Publish a collection, or a new version of a public one. Opened with
// `useOverlay()`; closes with the updated collection, or null if cancelled.
const props = defineProps<{ kind: ItemKind; collection: Collection }>()
const emit = defineEmits<{ close: [published: Collection | null] }>()

const api = useApi()
const notify = useNotify()

const includeNotes = ref(false)
const publishing = ref(false)
const next = props.collection.published_version + 1
const title = props.collection.is_public
  ? `Publicar la versión ${next} de «${props.collection.name}»`
  : `Publicar «${props.collection.name}»`

async function publish() {
  publishing.value = true
  try {
    emit('close', await publishCollection(api, props.kind, props.collection.id, includeNotes.value))
  }
  catch (failure) {
    // 422: more active items than an import takes.
    notify.failure(failure, 'No se ha podido publicar', 'La colección tiene demasiados elementos para publicarla.')
  }
  finally {
    publishing.value = false
  }
}
</script>

<template>
  <UModal :title="title" :close="{ onClick: () => emit('close', null) }" :ui="{ footer: 'justify-end' }">
    <template #body>
      <div class="space-y-4 text-sm text-toned">
        <p>
          Cualquier usuario podrá verla e importarla a su librería. Se publica tal como está ahora:
          lo que cambies después no se verá hasta que publiques otra versión.
        </p>
        <p>Solo se publican los elementos activos, con tus significados, ejemplos y lo que tienes oculto.</p>
        <UCheckbox
          v-model="includeNotes"
          label="Incluir mis notas"
          description="Las notas de las palabras, de sus significados y de los kanji."
          data-testid="publish-notes"
        />
      </div>
    </template>

    <template #footer>
      <UButton label="Cancelar" color="neutral" variant="outline" @click="emit('close', null)" />
      <UButton label="Publicar" icon="i-lucide-globe" :loading="publishing" data-testid="publish-confirm" @click="publish" />
    </template>
  </UModal>
</template>
