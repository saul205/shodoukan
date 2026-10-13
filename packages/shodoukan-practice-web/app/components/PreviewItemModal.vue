<script setup lang="ts">
import type { PracticeEntry, PracticeKanji } from '~/models/practice'

// A word or kanji of a public collection's preview, view-only, as importing it
// would give it: what the dictionary says plus what the collection's owner
// added (marked "de <owner>") and their note. Opened with `useOverlay()`.
const props = defineProps<{ item: { entry: PracticeEntry } | { kanji: PracticeKanji }; author: string }>()
const emit = defineEmits<{ close: [] }>()

const notes = computed(() => ('entry' in props.item ? props.item.entry.notes : props.item.kanji.notes))
</script>

<template>
  <UModal title="Detalle" :close="{ onClick: () => emit('close') }" :ui="{ content: 'sm:max-w-3xl', footer: 'justify-end' }">
    <template #body>
      <EntryDetail v-if="'entry' in item" :entry="item.entry" :author="author" view-only />
      <KanjiDetail v-else :kanji="item.kanji" :author="author" view-only />
      <div v-if="notes" class="mt-6 space-y-1 rounded-md bg-elevated/50 p-3" data-testid="item-notes">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted">Nota de {{ author }}</p>
        <p class="text-sm whitespace-pre-line text-toned">{{ notes }}</p>
      </div>
    </template>

    <template #footer>
      <UButton label="Cerrar" @click="emit('close')" />
    </template>
  </UModal>
</template>
