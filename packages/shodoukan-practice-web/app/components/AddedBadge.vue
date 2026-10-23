<script setup lang="ts">
// Marks what isn't the dictionary's: "propio" in the user's library, or
// "Nuevo" (with sparkles) in a public collection's preview, where it's what
// the collection adds. `word` for a whole word that isn't in the dictionary.
const props = withDefaults(defineProps<{ fromCollection?: boolean; word?: boolean; size?: 'sm' | 'md' }>(), {
  fromCollection: false,
  word: false,
  size: 'sm',
})

const label = computed(() => {
  if (props.fromCollection) return props.word ? 'Palabra nueva' : 'Nuevo'
  return props.word ? 'palabra propia' : 'propio'
})
</script>

<template>
  <UBadge
    :label="label"
    :icon="fromCollection ? 'i-lucide-sparkles' : undefined"
    color="primary"
    variant="soft"
    :size="size"
  />
</template>
