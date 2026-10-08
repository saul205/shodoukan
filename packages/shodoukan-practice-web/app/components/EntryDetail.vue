<script setup lang="ts">
import { shortenPos } from 'shodoukan-ui'
import type { EntryPart, PracticeEntry } from '~/models/practice'
import { entryHeadword, entryReading, sensesIn } from '~/utils/practice-text'
import { japaneseSentence, translatedSentence } from '~/utils/sentences'

// A library word: its headword and its senses in the meaning language, with
// their examples and notes. Editable (switches, own senses and meanings, sense
// notes: it emits, the page saves) or `view-only`, showing only what the user
// keeps enabled, as in the item detail opened from a session.
const props = withDefaults(defineProps<{
  entry: PracticeEntry
  viewOnly?: boolean
  saving?: boolean
}>(), { viewOnly: false, saving: false })

const emit = defineEmits<{
  'toggle': [part: EntryPart, id: number, enabled: boolean]
  'add-sense': [text: string]
  'remove-sense': [senseId: number]
  'add-gloss': [senseId: number, text: string]
  'edit-gloss': [glossId: number, text: string]
  'remove-gloss': [glossId: number]
  'sense-notes': [senseId: number, notes: string | null]
}>()

const { glossCode, lang, options: languages } = useMeaningLang()
const languageLabel = computed(() => languages.find(l => l.value === lang.value)?.label ?? lang.value)

function meaningsOf(sense: PracticeEntry['senses'][number]) {
  return sense.glosses.filter(g => g.lang === glossCode.value)
}

// Only the senses with a meaning in the chosen language; the rest belong to
// other languages. Read-only, only the enabled ones with a meaning still shown.
const senses = computed(() => {
  const inLanguage = sensesIn(props.entry, glossCode.value)
  return props.viewOnly
    ? inLanguage.filter(sense => sense.enabled && meaningsOf(sense).some(g => g.enabled))
    : inLanguage
})

const MAX_LENGTH = 500
const newSense = ref('')
const canAddSense = computed(() => {
  const text = newSense.value.trim()
  return !props.saving && text.length > 0 && text.length <= MAX_LENGTH
})

function addSense() {
  if (!canAddSense.value) return
  emit('add-sense', newSense.value.trim())
  newSense.value = ''
}

function examplesOf(sense: PracticeEntry['senses'][number]) {
  return props.viewOnly ? sense.examples.filter(e => e.enabled) : sense.examples
}
</script>

<template>
  <div class="space-y-8">
    <header class="space-y-2">
      <p v-if="entryReading(entry)" class="font-japanese text-sm text-muted">{{ entryReading(entry) }}</p>
      <h1 class="font-japanese text-4xl font-bold text-highlighted">{{ entryHeadword(entry) }}</h1>
      <div class="flex flex-wrap gap-1">
        <UBadge v-if="entry.jlpt" :label="`JLPT N${entry.jlpt}`" variant="soft" />
        <UBadge v-if="entry.is_common" label="común" color="success" variant="soft" />
        <UBadge v-if="entry.source_entry_id === null" label="palabra propia" color="primary" variant="soft" data-testid="own-word" />
      </div>
    </header>

    <section aria-labelledby="senses" class="space-y-4">
      <div class="flex items-baseline justify-between gap-2">
        <h2 id="senses" class="text-sm font-semibold uppercase tracking-wide text-muted">Significados</h2>
        <span class="text-xs text-dimmed">en {{ languageLabel }} · cámbialo en el menú lateral</span>
      </div>

      <p v-if="!senses.length" class="text-sm text-muted">
        Esta palabra no tiene significados en {{ languageLabel }}.
      </p>

      <UCard v-for="(sense, i) in senses" :key="sense.id" :ui="{ body: 'space-y-4' }" data-testid="sense">
        <div class="flex flex-wrap items-center gap-1.5">
          <USwitch
            v-if="!viewOnly"
            :model-value="sense.enabled"
            :disabled="saving"
            size="sm"
            :aria-label="sense.enabled ? 'Ocultar este significado entero' : 'Mostrar este significado entero'"
            data-testid="sense-switch"
            @update:model-value="emit('toggle', 'senses', sense.id, $event)"
          />
          <span class="text-sm text-dimmed">{{ i + 1 }}.</span>
          <UBadge v-for="pos in sense.pos" :key="pos" :label="shortenPos(pos)" color="neutral" variant="subtle" size="sm" />
          <span v-if="sense.misc.length || sense.info.length" class="text-xs text-muted italic">
            {{ [...sense.misc, ...sense.info].join(' · ') }}
          </span>
          <UBadge v-if="sense.origin === 'added'" label="propio" color="primary" variant="soft" size="sm" />
          <span v-if="!viewOnly && !sense.enabled" class="text-xs text-dimmed">oculto al practicar</span>
          <UButton
            v-if="!viewOnly && sense.origin === 'added'"
            icon="i-lucide-trash-2"
            color="error"
            variant="ghost"
            size="xs"
            class="ms-auto"
            aria-label="Eliminar este significado entero"
            :disabled="saving"
            data-testid="remove-sense"
            @click="emit('remove-sense', sense.id)"
          />
        </div>

        <div :class="{ 'opacity-60': !viewOnly && !sense.enabled }" class="space-y-4">
          <MeaningList
            :meanings="meaningsOf(sense)"
            :view-only="viewOnly"
            :disabled="saving"
            @toggle="(glossId, enabled) => emit('toggle', 'glosses', glossId, enabled)"
            @add="text => emit('add-gloss', sense.id, text)"
            @edit="(glossId, text) => emit('edit-gloss', glossId, text)"
            @remove="glossId => emit('remove-gloss', glossId)"
          />

          <div v-if="examplesOf(sense).length" class="space-y-2">
            <h3 class="text-xs font-medium uppercase tracking-wide text-dimmed">Ejemplos</h3>
            <div v-for="example in examplesOf(sense)" :key="example.id" class="flex items-start gap-3">
              <USwitch
                v-if="!viewOnly"
                :model-value="example.enabled"
                :disabled="saving"
                size="sm"
                class="mt-1"
                aria-label="Mostrar u ocultar el ejemplo"
                @update:model-value="emit('toggle', 'examples', example.id, $event)"
              />
              <div :class="{ 'opacity-50': !example.enabled }">
                <p class="font-japanese text-sm text-default">{{ japaneseSentence(example.sentences) }}</p>
                <p v-if="translatedSentence(example.sentences, glossCode)" class="text-sm text-muted">
                  {{ translatedSentence(example.sentences, glossCode) }}
                </p>
              </div>
            </div>
          </div>

          <p v-if="viewOnly && sense.notes" class="text-sm whitespace-pre-line text-toned" data-testid="sense-notes">
            {{ sense.notes }}
          </p>
          <NotesEditor
            v-else-if="!viewOnly"
            :notes="sense.notes"
            label="Nota de este significado"
            :saving="saving"
            @save="notes => emit('sense-notes', sense.id, notes)"
          />
        </div>
      </UCard>

      <form v-if="!viewOnly" class="flex gap-2" data-testid="add-sense" @submit.prevent="addSense">
        <UInput
          v-model="newSense"
          placeholder="Añadir un significado nuevo, aparte de los anteriores…"
          class="flex-1"
          :maxlength="MAX_LENGTH"
          :disabled="saving"
        />
        <UButton type="submit" icon="i-lucide-plus" label="Nuevo significado" variant="soft" :disabled="!canAddSense" />
      </form>
    </section>
  </div>
</template>
