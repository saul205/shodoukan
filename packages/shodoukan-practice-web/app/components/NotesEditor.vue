<script setup lang="ts">
// A note that saves itself when the user leaves the field, only if it changed.
const props = withDefaults(defineProps<{
  notes: string | null
  label?: string
  placeholder?: string
  saving?: boolean
}>(), {
  label: 'Notas',
  placeholder: 'Escribe una nota…',
  saving: false,
})

const emit = defineEmits<{ save: [notes: string | null] }>()

const MAX_LENGTH = 2000
const draft = ref(props.notes ?? '')

watch(() => props.notes, (value) => {
  draft.value = value ?? ''
})

const tooLong = computed(() => draft.value.length > MAX_LENGTH)

function save() {
  const cleaned = draft.value.trim() || null
  if (tooLong.value || cleaned === (props.notes ?? null)) return
  emit('save', cleaned)
}
</script>

<template>
  <UFormField
    :label="label"
    :hint="`${draft.length}/${MAX_LENGTH}`"
    :error="tooLong ? 'La nota es demasiado larga.' : undefined"
  >
    <UTextarea
      v-model="draft"
      :placeholder="placeholder"
      :rows="2"
      autoresize
      :maxrows="10"
      class="w-full"
      :loading="saving"
      @blur="save"
    />
  </UFormField>
</template>
