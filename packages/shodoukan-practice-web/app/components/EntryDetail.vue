<script setup lang="ts">
import { shortenPos } from 'shodoukan-ui'
import type { EntryPart, PracticeEntry } from '~/models/practice'
import { entryHeadword, entryReading, sensesIn } from '~/utils/practice-text'
import { japaneseSentence, translatedSentence } from '~/utils/sentences'

// A library word: its headword and its senses in the meaning language, with
// their examples and notes. Editable (switches, own meanings, sense notes:
// it emits, the page saves) or `view-only`, showing only what the user keeps
// enabled, as in the item detail opened from a session.
const props = withDefaults(defineProps<{
  entry: PracticeEntry
  viewOnly?: boolean
  saving?: boolean
}>(), { viewOnly: false, saving: false })

const emit = defineEmits<{
  'toggle': [part: EntryPart, id: number, enabled: boolean]
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
// other languages. Read-only, only those with a meaning still shown.
const senses = computed(() => {
  const inLanguage = sensesIn(props.entry, glossCode.value)
  return props.viewOnly
    ? inLanguage.filter(sense => meaningsOf(sense).some(g => g.enabled))
    : inLanguage
})

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

      <UCard v-for="(sense, i) in senses" :key="sense.id" :ui="{ body: 'space-y-4' }">
        <div class="flex flex-wrap items-center gap-1.5">
          <span class="text-sm text-dimmed">{{ i + 1 }}.</span>
          <UBadge v-for="pos in sense.pos" :key="pos" :label="shortenPos(pos)" color="neutral" variant="subtle" size="sm" />
          <span v-if="sense.misc.length || sense.info.length" class="text-xs text-muted italic">
            {{ [...sense.misc, ...sense.info].join(' · ') }}
          </span>
        </div>

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
      </UCard>
    </section>
  </div>
</template>
