<script setup lang="ts">
import type { Origin } from '~/models/practice'
import { isKana } from '~/utils/own-entry'

// A word's spellings or readings: each one switched on or off; the user's own
// ("propio") can also be deleted, and new ones added at the end. Readings
// only take kana (`kana`). The parent saves: `@add` arrives as the `onAdd`
// prop, so the box waits for the save and keeps its text if it fails.

export interface FormItem {
  id: number
  text: string
  enabled: boolean
  origin: Origin
}

const props = withDefaults(defineProps<{
  items: FormItem[]
  addLabel: string
  kana?: boolean
  disabled?: boolean
  /** Saves a new form; resolves to whether it was saved. */
  onAdd?: (text: string) => Promise<boolean>
}>(), { kana: false, disabled: false })

const emit = defineEmits<{
  toggle: [id: number, enabled: boolean]
  remove: [id: number]
}>()

const MAX_LENGTH = 50

const newText = ref('')
const pending = ref(false)
const text = computed(() => newText.value.trim())
const invalid = computed(() => props.kana && text.value.length > 0 && !isKana(text.value))
const canAdd = computed(() => !props.disabled && !pending.value && text.value.length > 0 && text.value.length <= MAX_LENGTH && !invalid.value)

async function add() {
  if (!canAdd.value || !props.onAdd) return
  pending.value = true
  try {
    if (await props.onAdd(text.value)) newText.value = ''
  }
  finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="space-y-2">
    <div v-for="item in items" :key="item.id" class="flex items-center gap-2" data-testid="form-item">
      <USwitch
        :model-value="item.enabled"
        :disabled="disabled"
        :label="item.text"
        :ui="{ label: 'font-japanese' }"
        class="flex-1"
        @update:model-value="emit('toggle', item.id, $event)"
      />
      <template v-if="item.origin === 'added'">
        <UBadge label="propio" color="primary" variant="soft" size="sm" />
        <UButton
          icon="i-lucide-trash-2"
          color="error"
          variant="ghost"
          size="xs"
          :aria-label="`Eliminar ${item.text}`"
          :disabled="disabled"
          data-testid="remove-form"
          @click="emit('remove', item.id)"
        />
      </template>
    </div>

    <form class="flex gap-2" @submit.prevent="add">
      <UInput
        v-model="newText"
        :placeholder="addLabel"
        size="sm"
        class="flex-1 font-japanese"
        :maxlength="MAX_LENGTH"
        :disabled="disabled || pending"
        :color="invalid ? 'error' : undefined"
        :highlight="invalid"
      />
      <UButton type="submit" icon="i-lucide-plus" size="sm" variant="soft" aria-label="Añadir" :loading="pending" :disabled="!canAdd" />
    </form>
    <p v-if="invalid" class="text-xs text-error">Escríbela en kana (hiragana o katakana).</p>
  </div>
</template>
