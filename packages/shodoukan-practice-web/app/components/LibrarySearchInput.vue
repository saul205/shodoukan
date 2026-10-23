<script setup lang="ts">
// Search box for the library and collections. The model updates once typing
// pauses (300 ms) so each keystroke isn't a request; Enter and clearing
// update it at once.
const DELAY_MS = 300

const model = defineModel<string>({ default: '' })

withDefaults(defineProps<{ placeholder?: string }>(), {
  placeholder: 'Buscar por kanji, kana, romaji o significado',
})

const draft = ref(model.value)
let timer: ReturnType<typeof setTimeout> | undefined

// The model can change from outside (the URL, a tab switch): follow it.
watch(model, (value) => {
  if (value !== draft.value.trim()) draft.value = value
})

function commit() {
  clearTimeout(timer)
  const value = draft.value.trim()
  if (value !== model.value) model.value = value
}

function onInput(value: string) {
  draft.value = value
  clearTimeout(timer)
  timer = setTimeout(commit, DELAY_MS)
}

function clear() {
  draft.value = ''
  commit()
}

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <UInput
    :model-value="draft"
    icon="i-lucide-search"
    :placeholder="placeholder"
    :aria-label="placeholder"
    @update:model-value="value => onInput(String(value ?? ''))"
    @keydown.enter.prevent="commit"
  >
    <template v-if="draft" #trailing>
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="link"
        size="sm"
        aria-label="Borrar la búsqueda"
        @click="clear"
      />
    </template>
  </UInput>
</template>
