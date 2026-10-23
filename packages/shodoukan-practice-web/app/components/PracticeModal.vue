<script setup lang="ts">
import { DEFAULT_MODE, DEFAULT_REPETITIONS, type PracticeItem, type PracticeMode } from '~/utils/writing-practice'

// Writing practice of a few items without leaving the page: from an
// exercise session, which stays as it was underneath. Opened with
// `useOverlay()`. Full screen on a phone, where the pad needs the room.
const props = defineProps<{ items: PracticeItem[]; title?: string }>()
const emit = defineEmits<{ close: [] }>()

const mode = ref<PracticeMode>(DEFAULT_MODE)
const finished = ref(false)
const run = ref(0)

function again() {
  finished.value = false
  run.value++
}
</script>

<template>
  <UModal
    :title="title ?? 'Practicar escritura'"
    :close="{ onClick: () => emit('close') }"
    :ui="{ content: 'max-sm:h-dvh max-sm:max-h-none max-sm:rounded-none sm:max-w-2xl sm:h-[85dvh]', body: 'flex min-h-0 flex-1 flex-col' }"
    data-testid="practice-modal"
  >
    <template #body>
      <div v-if="finished" class="flex flex-1 flex-col items-center justify-center gap-4 text-center" data-testid="practice-finished">
        <UIcon name="i-lucide-circle-check" class="size-10 text-success" />
        <p class="text-highlighted">Práctica terminada</p>
        <div class="flex gap-2">
          <UButton label="Otra vez" icon="i-lucide-rotate-ccw" color="neutral" variant="outline" @click="again" />
          <UButton label="Volver" @click="emit('close')" />
        </div>
      </div>
      <WritingPractice
        v-else
        :key="run"
        v-model:mode="mode"
        :items="props.items"
        :repetitions="DEFAULT_REPETITIONS"
        @finished="finished = true"
      />
    </template>
  </UModal>
</template>
