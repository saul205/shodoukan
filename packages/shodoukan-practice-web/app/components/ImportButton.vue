<script setup lang="ts">
// Import a dictionary result into the library, or open the copy if it's
// already there (`practiceId`).
const props = defineProps<{
  practiceId: number | null | undefined
  /** Where the library copy is, e.g. "/library/entries/3". */
  libraryPath: (id: number) => string
  loading?: boolean
}>()

defineEmits<{ import: [] }>()
</script>

<template>
  <UButton
    v-if="props.practiceId"
    :to="libraryPath(props.practiceId)"
    label="En tu librería"
    icon="i-lucide-check"
    color="success"
    variant="soft"
    size="sm"
  />
  <UButton
    v-else
    label="Importar"
    icon="i-lucide-plus"
    size="sm"
    :loading="loading"
    @click="$emit('import')"
  />
</template>
