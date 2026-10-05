<script setup lang="ts">
import type { ItemKind, PracticeEntry, PracticeKanji } from '~/models/practice'
import { getLibraryEntry, getLibraryKanji } from '~/services/library'
import { apiStatus } from '~/utils/api-error'

// A library item's full detail, view-only, without leaving the session.
// Opened with `useOverlay()`. "Abrir en la librería" goes to the item's page
// in the same window; its back button returns to `returnTo` (the opening
// page's path, `?from=`: a session picks up where it was).
const props = defineProps<{ kind: ItemKind; itemId: number; returnTo?: string }>()
const emit = defineEmits<{ close: [] }>()

const api = useApi()

const { data: item, status, error } = useAsyncData(
  `item-detail-${props.kind}-${props.itemId}`,
  async (): Promise<{ entry: PracticeEntry } | { kanji: PracticeKanji }> =>
    props.kind === 'entries'
      ? { entry: await getLibraryEntry(api, props.itemId) }
      : { kanji: await getLibraryKanji(api, props.itemId) },
)

async function openInLibrary() {
  emit('close')
  await navigateTo({
    path: `/library/${props.kind}/${props.itemId}`,
    query: props.returnTo ? { from: props.returnTo } : {},
  })
}
</script>

<template>
  <UModal
    title="Detalle"
    :close="{ onClick: () => emit('close') }"
    :ui="{ content: 'sm:max-w-3xl', footer: 'justify-end' }"
  >
    <template #body>
      <USkeleton v-if="status === 'pending' && !item" class="h-64 w-full" />
      <UEmpty
        v-else-if="apiStatus(error) === 404"
        icon="i-lucide-search-x"
        title="Ya no está en tu librería"
      />
      <UAlert
        v-else-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="No se ha podido cargar"
      />
      <template v-else-if="item">
        <EntryDetail v-if="'entry' in item" :entry="item.entry" view-only />
        <KanjiDetail v-else :kanji="item.kanji" view-only />
        <p
          v-if="'entry' in item ? item.entry.notes : item.kanji.notes"
          class="mt-6 rounded-md bg-elevated/50 p-3 text-sm whitespace-pre-line text-toned"
          data-testid="item-notes"
        >
          {{ 'entry' in item ? item.entry.notes : item.kanji.notes }}
        </p>
      </template>
    </template>

    <template #footer>
      <UButton
        label="Abrir en la librería"
        icon="i-lucide-library-big"
        color="neutral"
        variant="ghost"
        data-testid="open-in-library"
        @click="openInLibrary"
      />
      <UButton label="Cerrar" @click="emit('close')" />
    </template>
  </UModal>
</template>
