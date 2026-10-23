<script setup lang="ts">
// Import a dictionary result into the library or, once it's there, remove it:
// the "in your library" check turns into "remove" on hover or keyboard focus.
// `iconOnly` is for a card's corner; the tooltip and aria-label say what a
// click does.
const props = defineProps<{
  imported: boolean
  loading?: boolean
  iconOnly?: boolean
}>()

defineEmits<{ import: [], remove: [] }>()

// The root is UTooltip, which renders no element: classes go to the button.
defineOptions({ inheritAttrs: false })

const active = ref(false)
const removing = computed(() => props.imported && active.value)

const look = computed(() => {
  if (removing.value) return { label: 'Quitar', icon: 'i-lucide-trash-2', color: 'error' as const, tip: 'Quitar de tu librería' }
  if (props.imported) return { label: 'En tu librería', icon: 'i-lucide-check', color: 'success' as const, tip: 'En tu librería · clic para quitar' }
  return { label: 'Importar', icon: 'i-lucide-plus', color: 'primary' as const, tip: 'Importar a tu librería' }
})

// Back to the check once the item is removed (or imported) under the pointer.
watch(() => props.imported, () => {
  active.value = false
})
</script>

<template>
  <UTooltip :text="look.tip">
    <UButton
      v-bind="$attrs"
      :label="iconOnly ? undefined : look.label"
      :aria-label="look.tip"
      :icon="look.icon"
      :color="look.color"
      :variant="imported || iconOnly ? 'soft' : 'solid'"
      :loading="loading"
      size="sm"
      @mouseenter="active = true"
      @mouseleave="active = false"
      @focus="active = true"
      @blur="active = false"
      @click="imported ? $emit('remove') : $emit('import')"
    />
  </UTooltip>
</template>
