<script setup lang="ts">
import type { PracticeSentence } from '~/models/practice'
import { sentencePieces, sentenceTranslation } from '~/utils/sentences'

// The sentences of a word under one of its senses, the word's gap
// highlighted. A dictionary sentence can only be switched on or off; the
// user's own can also be rewritten and deleted, and new ones added (a Japanese
// sentence and, optionally, its translation in the meaning language: the word
// is found in it, inflected or not). Each one opens in the sentence editor,
// where its words are marked and linked. `view-only` lists only the shown
// ones, as text.
//
// The parent saves: `@add` / `@rewrite` arrive as the `onAdd` / `onRewrite`
// props, so the form waits for the save and stays open with its text if it
// fails.

const props = withDefaults(defineProps<{
  sentences: PracticeSentence[]
  /** The word whose gap is highlighted. */
  entryId?: number | null
  glossLang: string // ISO 639-2, e.g. "eng"
  disabled?: boolean
  viewOnly?: boolean
  /** In a public collection's preview: the added sentences are what it brings ("Nuevo"). */
  fromCollection?: boolean
  /** Saves a new sentence; resolves to whether it was saved. */
  onAdd?: (japanese: string, translation: string | null) => Promise<boolean>
  /** Saves an own sentence's new text; resolves to whether it was saved. */
  onRewrite?: (id: number, japanese: string, translation: string | null) => Promise<boolean>
}>(), { entryId: null, disabled: false, viewOnly: false, fromCollection: false })

const emit = defineEmits<{
  toggle: [id: number, active: boolean]
  remove: [id: number]
}>()

const MAX_LENGTH = 500

const shown = computed(() => (props.viewOnly ? props.sentences.filter(s => s.is_active) : props.sentences))

// One form adds a new sentence or, with `editingId`, rewrites an own one.
const adding = ref(false)
const editingId = ref<number | null>(null)
const japanese = ref('')
const translation = ref('')
const pending = ref(false)

const canSave = computed(() => {
  const text = japanese.value.trim()
  return !props.disabled && !pending.value && text.length > 0 && text.length <= MAX_LENGTH && translation.value.length <= MAX_LENGTH
})

function open(sentence?: PracticeSentence) {
  editingId.value = sentence?.id ?? null
  japanese.value = sentence?.text ?? ''
  translation.value = sentence ? sentenceTranslation(sentence, props.glossLang) : ''
  adding.value = !sentence
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
      : await props.onRewrite?.(id, text, translated)
    if (saved) close()
  }
  finally {
    pending.value = false
  }
}
</script>

<template>
  <div v-if="shown.length || !viewOnly" class="space-y-2">
    <h3 class="text-xs font-medium uppercase tracking-wide text-dimmed">Frases</h3>

    <div v-for="sentence in shown" :key="sentence.id" class="flex items-start gap-3" data-testid="sentence">
      <USwitch
        v-if="!viewOnly"
        :model-value="sentence.is_active"
        :disabled="disabled"
        size="sm"
        class="mt-1"
        aria-label="Mostrar u ocultar la frase"
        @update:model-value="emit('toggle', sentence.id, $event)"
      />
      <form
        v-if="editingId === sentence.id"
        class="flex-1 space-y-2"
        data-testid="sentence-form"
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
      <div v-else class="flex-1" :class="{ 'opacity-50': !sentence.is_active }">
        <p class="font-japanese text-sm text-default">
          <template v-for="(piece, i) in sentencePieces(sentence, entryId)" :key="i">
            <span
              v-if="piece.gap === 'own'"
              class="underline decoration-primary decoration-2 underline-offset-4"
              data-testid="own-gap"
            >{{ piece.text }}</span>
            <span v-else>{{ piece.text }}</span>
          </template>
          <AddedBadge v-if="sentence.origin === 'added'" :from-collection="fromCollection" />
        </p>
        <p v-if="sentenceTranslation(sentence, glossLang)" class="text-sm text-muted">
          {{ sentenceTranslation(sentence, glossLang) }}
        </p>
      </div>
      <template v-if="!viewOnly && editingId !== sentence.id">
        <UButton
          icon="i-lucide-text-cursor-input"
          color="neutral"
          variant="ghost"
          size="xs"
          aria-label="Abrir en el editor de frases"
          :to="`/library/sentences/${sentence.id}`"
          data-testid="open-sentence"
        />
        <template v-if="sentence.origin === 'added'">
          <UButton
            icon="i-lucide-pencil"
            color="neutral"
            variant="ghost"
            size="xs"
            aria-label="Editar frase"
            :disabled="disabled"
            data-testid="edit-sentence"
            @click="open(sentence)"
          />
          <UButton
            icon="i-lucide-trash-2"
            color="error"
            variant="ghost"
            size="xs"
            aria-label="Eliminar frase"
            :disabled="disabled"
            data-testid="remove-sentence"
            @click="emit('remove', sentence.id)"
          />
        </template>
      </template>
    </div>

    <template v-if="!viewOnly">
      <form v-if="adding" class="space-y-2" data-testid="sentence-form" @submit.prevent="save" @keydown.esc="close">
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
        label="Añadir una frase propia"
        size="xs"
        color="neutral"
        variant="ghost"
        :disabled="disabled"
        data-testid="add-sentence"
        @click="open()"
      />
    </template>
  </div>
</template>
