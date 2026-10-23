<script setup lang="ts">
// A yes/no question, opened with `useOverlay()`; resolves to true when confirmed.
withDefaults(defineProps<{
  title: string
  description?: string
  confirmLabel?: string
}>(), { description: undefined, confirmLabel: 'Eliminar' })

const emit = defineEmits<{ close: [confirmed: boolean] }>()
</script>

<template>
  <UModal
    :title="title"
    :description="description"
    :close="{ onClick: () => emit('close', false) }"
    :ui="{ footer: 'justify-end' }"
  >
    <template #footer>
      <UButton label="Cancelar" color="neutral" variant="outline" @click="emit('close', false)" />
      <UButton :label="confirmLabel" color="error" @click="emit('close', true)" />
    </template>
  </UModal>
</template>
