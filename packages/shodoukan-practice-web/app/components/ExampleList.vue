<script setup lang="ts">
import type { PracticeExample } from '~/models/practice'
import { japaneseSentence, translatedSentence } from '~/utils/sentences'

// A sense's example sentences. The dictionary's can only be switched on or
// off; the user's own can also be rewritten and deleted, and new ones added
// at the end: a Japanese sentence and, optionally, its translation in the
// meaning language. `view-only` lists only the shown ones, as text.
//
// The parent saves: `@add` / `@edit` arrive as the `onAdd` / `onEdit` props,
// so the form waits for the save and stays open with its text if it fails.

const props = withDefaults(defineProps<{
  examples: PracticeExample[]
  glossLang: string // ISO 639-2, e.g. "eng"
  disabled?: boolean
  viewOnly?: boolean
  /** Saves a new example; resolves to whether it was saved. */
  onAdd?: (japanese: string, translation: string | null) => Promise<boolean>
  /** Saves an own example's new text; resolves to whether it was saved. */
  onEdit?: (id: number, japanese: string, translation: string | null) => Promise<boolean>
}>(), { disabled: false, viewOnly: false })

const emit = defineEmits<{
  toggle: [id: number, enabled: boolean]
  remove: [id: number]
}>()

const MAX_LENGTH = 500

const shown = computed(() => props.viewOnly ? props.examples.filter(e => e.enabled) : props.examples)

// One form adds a new example or, with `editingId`, rewrites an own one.
const adding = ref(false)
const editingId = ref<number | null>(null)
const japanese = ref('')
const translation = ref('')
const pending = ref(false)

const canSave = computed(() => {
  const text = japanese.value.trim()
  return !props.disabled && !pending.value && text.length > 0 && text.length <= MAX_LENGTH && translation.value.length <= MAX_LENGTH
})

function open(example?: PracticeExample) {
  editingId.value = example?.id ?? null
  japanese.value = example ? japaneseSentence(example.sentences) : ''
  translation.value = example ? translatedSentence(example.sentences, props.glossLang) : ''
  adding.value = !example
}

function close() {
  adding.value = false
  editingId.value = null
}

async function save() {
  if (!canSave.value) return
  const text = japanese.value.trim()
  const translated = translation.value.trim() || null
  const id = editingId.value
  pending.value = true
  try {
    const saved = id === null
      ? await props.onAdd?.(text, translated)
      : await props.onEdit?.(id, text, translated)
    if (saved) close()
  }
  finally {
    pending.value = false
  }
}
</script>

<template>
  <div v-if="shown.length || !viewOnly" class="space-y-2">
    <h3 class="text-xs font-medium uppercase tracking-wide text-dimmed">Ejemplos</h3>

    <div v-for="example in shown" :key="example.id" class="flex items-start gap-3" data-testid="example">
      <USwitch
        v-if="!viewOnly"
        :model-value="example.enabled"
        :disabled="disabled"
        size="sm"
        class="mt-1"
        aria-label="Mostrar u ocultar el ejemplo"
        @update:model-value="emit('toggle', example.id, $event)"
      />
      <form
        v-if="editingId === example.id"
        class="flex-1 space-y-2"
        data-testid="example-form"
        @submit.prevent="save"
        @keydown.esc="close"
      >
        <UInput v-model="japanese" placeholder="Frase en japonés" class="w-full font-japanese" :maxlength="MAX_LENGTH" :disabled="pending" autofocus />
        <UInput v-model="translation" placeholder="Traducción (opcional)" class="w-full" :maxlength="MAX_LENGTH" :disabled="pending" />
        <div class="flex gap-2">
          <UButton type="submit" label="Guardar" size="sm" :loading="pending" :disabled="!canSave" />
          <UButton label="Cancelar" size="sm" color="neutral" variant="ghost" @click="close" />
        </div>
      </form>
      <div v-else class="flex-1" :class="{ 'opacity-50': !example.enabled }">
        <p class="font-japanese text-sm text-default">
          {{ japaneseSentence(example.sentences) }}
          <UBadge v-if="example.origin === 'added'" label="propio" color="primary" variant="soft" size="sm" />
        </p>
        <p v-if="translatedSentence(example.sentences, glossLang)" class="text-sm text-muted">
          {{ translatedSentence(example.sentences, glossLang) }}
        </p>
      </div>
      <template v-if="!viewOnly && example.origin === 'added' && editingId !== example.id">
        <UButton
          icon="i-lucide-pencil"
          color="neutral"
          variant="ghost"
          size="xs"
          aria-label="Editar ejemplo"
          :disabled="disabled"
          data-testid="edit-example"
          @click="open(example)"
        />
        <UButton
          icon="i-lucide-trash-2"
          color="error"
          variant="ghost"
          size="xs"
          aria-label="Eliminar ejemplo"
          :disabled="disabled"
          data-testid="remove-example"
          @click="emit('remove', example.id)"
        />
      </template>
    </div>

    <template v-if="!viewOnly">
      <form v-if="adding" class="space-y-2" data-testid="example-form" @submit.prevent="save" @keydown.esc="close">
        <UInput v-model="japanese" placeholder="Frase en japonés" class="w-full font-japanese" :maxlength="MAX_LENGTH" :disabled="pending" autofocus />
        <UInput v-model="translation" placeholder="Traducción (opcional)" class="w-full" :maxlength="MAX_LENGTH" :disabled="pending" />
        <div class="flex gap-2">
          <UButton type="submit" label="Añadir" size="sm" :loading="pending" :disabled="!canSave" />
          <UButton label="Cancelar" size="sm" color="neutral" variant="ghost" @click="close" />
        </div>
      </form>
      <UButton
        v-else
        icon="i-lucide-plus"
        label="Añadir un ejemplo propio"
        size="xs"
        color="neutral"
        variant="ghost"
        :disabled="disabled"
        data-testid="add-example"
        @click="open()"
      />
    </template>
  </div>
</template>
