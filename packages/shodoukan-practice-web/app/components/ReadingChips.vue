<script setup lang="ts">
import type { PracticeReadingItem } from '~/models/practice'

// Readings as chips that toggle on click: shown ones are filled, hidden ones
// faded and struck through. Lighter to scan than a switch per reading when a
// kanji has many (兄 has ten). `view-only` shows only the shown ones, as badges.
const props = defineProps<{
  readings: PracticeReadingItem[]
  disabled?: boolean
  viewOnly?: boolean
}>()

const shown = computed(() => props.readings.filter(reading => reading.enabled))

defineEmits<{ toggle: [id: number, enabled: boolean] }>()
</script>

<template>
  <div v-if="viewOnly" class="flex flex-wrap gap-1.5">
    <UBadge
      v-for="reading in shown"
      :key="reading.id"
      :label="reading.text"
      color="primary"
      variant="soft"
      size="lg"
      class="font-japanese"
    />
  </div>

  <div v-else class="flex flex-wrap gap-1.5">
    <UTooltip
      v-for="reading in readings"
      :key="reading.id"
      :text="reading.enabled ? 'Ocultar esta lectura' : 'Mostrar esta lectura'"
    >
      <UButton
        :label="reading.text"
        :aria-pressed="reading.enabled"
        :color="reading.enabled ? 'primary' : 'neutral'"
        :variant="reading.enabled ? 'soft' : 'outline'"
        :disabled="disabled"
        size="sm"
        class="font-japanese"
        :class="{ 'line-through opacity-60': !reading.enabled }"
        @click="$emit('toggle', reading.id, !reading.enabled)"
      />
    </UTooltip>
  </div>
</template>
