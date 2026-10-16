<script setup lang="ts">
import type { PracticeEntry, PracticeKanji } from '~/models/practice'

// A word or kanji of a public collection's preview, view-only, as importing it
// would give it to someone who doesn't have it: what the dictionary says plus
// what the collection adds (marked "Nuevo") and its notes. Opened with
// `useOverlay()`.
const props = defineProps<{ item: { entry: PracticeEntry } | { kanji: PracticeKanji } }>()
const emit = defineEmits<{ close: [] }>()

const notes = computed(() => ('entry' in props.item ? props.item.entry.notes : props.item.kanji.notes))
</script>

<template>
  <UModal title="Detalle" :close="{ onClick: () => emit('close') }" :ui="{ content: 'sm:max-w-3xl', footer: 'justify-end' }">
    <template #body>
      <EntryDetail v-if="'entry' in item" :entry="item.entry" from-collection view-only />
      <KanjiDetail v-else :kanji="item.kanji" from-collection view-only />
      <div v-if="notes" class="mt-6 space-y-1 rounded-md bg-elevated/50 p-3" data-testid="item-notes">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted">Nota de la colección</p>
        <p class="text-sm whitespace-pre-line text-toned">{{ notes }}</p>
      </div>
    </template>

    <template #footer>
      <UButton label="Cerrar" @click="emit('close')" />
    </template>
  </UModal>
</template>
