<script setup lang="ts">
import type { Origin } from '~/models/practice'

// An editable list of meanings. The dictionary's own meanings can only be
// switched on or off; the user's own can also be edited and deleted, and new
// ones added at the end. `view-only` lists only the shown ones, as text.

export interface MeaningItem {
  id: number
  text: string
  enabled: boolean
  origin: Origin
}

const props = withDefaults(defineProps<{
  meanings: MeaningItem[]
  disabled?: boolean
  viewOnly?: boolean
}>(), { disabled: false, viewOnly: false })

const emit = defineEmits<{
  toggle: [id: number, enabled: boolean]
  add: [text: string]
  edit: [id: number, text: string]
  remove: [id: number]
}>()

const MAX_LENGTH = 500

const newText = ref('')
const editingId = ref<number | null>(null)
const editText = ref('')

const shown = computed(() => props.meanings.filter(meaning => meaning.enabled))

const canAdd = computed(() => {
  const text = newText.value.trim()
  return !props.disabled && text.length > 0 && text.length <= MAX_LENGTH
})

function add() {
  if (!canAdd.value) return
  emit('add', newText.value.trim())
  newText.value = ''
}

function startEdit(meaning: MeaningItem) {
  editingId.value = meaning.id
  editText.value = meaning.text
}

function confirmEdit(meaning: MeaningItem) {
  const text = editText.value.trim()
  editingId.value = null
  if (text && text.length <= MAX_LENGTH && text !== meaning.text) emit('edit', meaning.id, text)
}
</script>

<template>
  <div v-if="viewOnly">
    <ul v-if="shown.length" class="list-inside list-disc space-y-0.5 text-default">
      <li v-for="meaning in shown" :key="meaning.id" data-testid="meaning">
        {{ meaning.text }}
        <UBadge v-if="meaning.origin === 'added'" label="propio" color="primary" variant="soft" size="sm" />
      </li>
    </ul>
    <p v-else class="text-sm text-muted">Sin significados en este idioma.</p>
  </div>

  <div v-else class="space-y-2">
    <ul v-if="meanings.length" class="space-y-1">
      <li
        v-for="meaning in meanings"
        :key="meaning.id"
        class="flex items-center gap-3 rounded-md px-2 py-1 hover:bg-elevated/50"
        data-testid="meaning"
      >
        <USwitch
          :model-value="meaning.enabled"
          :disabled="disabled"
          size="sm"
          :aria-label="meaning.enabled ? 'Ocultar significado' : 'Mostrar significado'"
          @update:model-value="emit('toggle', meaning.id, $event)"
        />

        <UInput
          v-if="editingId === meaning.id"
          v-model="editText"
          size="sm"
          class="flex-1"
          autofocus
          :maxlength="MAX_LENGTH"
          @keydown.enter.prevent="confirmEdit(meaning)"
          @keydown.esc="editingId = null"
          @blur="confirmEdit(meaning)"
        />
        <span
          v-else
          class="flex-1"
          :class="meaning.enabled ? 'text-default' : 'text-dimmed line-through'"
        >{{ meaning.text }}</span>

        <template v-if="meaning.origin === 'added'">
          <UBadge label="propio" color="primary" variant="soft" size="sm" />
          <UButton
            icon="i-lucide-pencil"
            color="neutral"
            variant="ghost"
            size="xs"
            aria-label="Editar significado"
            :disabled="disabled"
            data-testid="edit"
            @click="startEdit(meaning)"
          />
          <UButton
            icon="i-lucide-trash-2"
            color="error"
            variant="ghost"
            size="xs"
            aria-label="Eliminar significado"
            :disabled="disabled"
            data-testid="remove"
            @click="emit('remove', meaning.id)"
          />
        </template>
      </li>
    </ul>
    <p v-else class="px-2 text-sm text-muted">Sin significados en este idioma.</p>

    <form class="flex gap-2" @submit.prevent="add">
      <UInput
        v-model="newText"
        placeholder="Añadir un significado propio…"
        size="sm"
        class="flex-1"
        :maxlength="MAX_LENGTH"
        :disabled="disabled"
      />
      <UButton type="submit" icon="i-lucide-plus" label="Añadir" size="sm" variant="soft" :disabled="!canAdd" />
    </form>
  </div>
</template>
