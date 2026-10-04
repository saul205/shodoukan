<script setup lang="ts">
import { shortenPos } from 'shodoukan-ui'
import ConfirmModal from '~/components/ConfirmModal.vue'
import type { EntryPart, PracticeEntry } from '~/models/practice'
import {
  addGloss,
  editGloss,
  getLibraryEntry,
  removeGloss,
  removeLibraryEntry,
  setEntryActive,
  setEntryNotes,
  setEntryPartEnabled,
  setSenseNotes,
} from '~/services/library'
import { getDictionaryEntryKanji } from '~/services/dictionary'
import { entryHeadword, entryReading, sensesIn } from '~/utils/practice-text'
import { japaneseSentence, translatedSentence } from '~/utils/sentences'

// A word of the library and its customisation. The same page opens from the
// library and from a collection (`?collection=<id>`, for the back link).
// Every change is saved as it's made.

const route = useRoute()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()
const { glossCode, lang, options: languages } = useMeaningLang()
const back = useBackLink('entries')

const id = computed(() => Number(route.params.id))
const { item: entry, status, saving, save } = useEditableItem<PracticeEntry>(
  () => `library-entry-${id.value}`,
  () => getLibraryEntry(api, id.value),
)

const languageLabel = computed(() => languages.find(l => l.value === lang.value)?.label ?? lang.value)

// The word's kanji come from the dictionary, with whether each one is imported.
const kanjiStatus = useImportStatus()
const sourceId = computed(() => entry.value?.source_entry_id)
const { data: wordKanji } = useAsyncData(
  () => `library-entry-kanji-${sourceId.value}`,
  async () => {
    if (sourceId.value === undefined) return null
    const kanji = await getDictionaryEntryKanji(api, sourceId.value)
    await kanjiStatus.refresh([], kanji.map(k => k.literal))
    return kanji
  },
  { watch: [sourceId] },
)

// Only the senses with a meaning in the chosen language; the rest belong to other languages.
const senses = computed(() => (entry.value ? sensesIn(entry.value, glossCode.value) : []))

function meaningsOf(sense: PracticeEntry['senses'][number]) {
  return sense.glosses.filter(g => g.lang === glossCode.value)
}

const toggle = (part: EntryPart, itemId: number, enabled: boolean) =>
  save(() => setEntryPartEnabled(api, id.value, part, itemId, enabled))

async function remove() {
  const confirmed = await overlay.create(ConfirmModal).open({
    title: '¿Quitar de tu librería?',
    description: 'Se borran tus notas y significados propios, y sale de todas tus colecciones. Podrás volver a importarla desde el diccionario.',
    confirmLabel: 'Quitar',
  }).result
  if (!confirmed) return
  try {
    await removeLibraryEntry(api, id.value)
    notify.success('Quitada de tu librería')
    await navigateTo(back.value.to)
  }
  catch (error) {
    notify.failure(error, 'No se ha podido quitar')
  }
}
</script>

<template>
  <AppPanel :title="entry ? entryHeadword(entry) : 'Palabra'">
    <template #leading>
      <UButton :to="back.to" icon="i-lucide-arrow-left" color="neutral" variant="ghost" :aria-label="back.label" />
    </template>
    <template v-if="entry" #actions>
      <UButton
        :to="`/dictionary/entries/${entry.source_entry_id}`"
        icon="i-lucide-book-open"
        label="Abrir en el diccionario"
        color="neutral"
        variant="ghost"
        class="hidden sm:inline-flex"
      />
      <UButton icon="i-lucide-trash-2" label="Quitar" color="error" variant="soft" @click="remove" />
    </template>

    <div v-if="status === 'pending' && !entry" class="space-y-3">
      <USkeleton class="h-16 w-48" />
      <USkeleton v-for="i in 3" :key="i" class="h-24 w-full" />
    </div>

    <UEmpty
      v-else-if="!entry"
      icon="i-lucide-search-x"
      title="Esta palabra no está en tu librería"
      :actions="[{ label: back.label, to: back.to, icon: 'i-lucide-arrow-left' }]"
    />

    <div v-else class="grid gap-8 lg:grid-cols-3">
      <div class="space-y-8 lg:col-span-2">
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
              :disabled="saving"
              @toggle="(glossId, enabled) => toggle('glosses', glossId, enabled)"
              @add="text => save(() => addGloss(api, id, sense.id, text, glossCode))"
              @edit="(glossId, text) => save(() => editGloss(api, id, glossId, text))"
              @remove="glossId => save(() => removeGloss(api, id, glossId))"
            />

            <div v-if="sense.examples.length" class="space-y-2">
              <h3 class="text-xs font-medium uppercase tracking-wide text-dimmed">Ejemplos</h3>
              <div v-for="example in sense.examples" :key="example.id" class="flex items-start gap-3">
                <USwitch
                  :model-value="example.enabled"
                  :disabled="saving"
                  size="sm"
                  class="mt-1"
                  aria-label="Mostrar u ocultar el ejemplo"
                  @update:model-value="toggle('examples', example.id, $event)"
                />
                <div :class="{ 'opacity-50': !example.enabled }">
                  <p class="font-japanese text-sm text-default">{{ japaneseSentence(example.sentences) }}</p>
                  <p v-if="translatedSentence(example.sentences, glossCode)" class="text-sm text-muted">
                    {{ translatedSentence(example.sentences, glossCode) }}
                  </p>
                </div>
              </div>
            </div>

            <NotesEditor
              :notes="sense.notes"
              label="Nota de este significado"
              :saving="saving"
              @save="notes => save(() => setSenseNotes(api, id, sense.id, notes))"
            />
          </UCard>
        </section>

        <EntryKanjiList v-if="wordKanji" :kanji="wordKanji" :status="kanjiStatus" link-to="library" />
      </div>

      <aside class="space-y-6">
        <UCard :ui="{ body: 'space-y-3' }">
          <USwitch
            :model-value="entry.is_active"
            :disabled="saving"
            label="Activa para practicar"
            description="Las inactivas siguen en tu librería y colecciones, pero no se practican."
            @update:model-value="active => save(() => setEntryActive(api, id, active))"
          />
        </UCard>

        <section aria-labelledby="notes">
          <h2 id="notes" class="sr-only">Notas</h2>
          <NotesEditor
            :notes="entry.notes"
            label="Notas"
            placeholder="Trucos, contexto, dudas…"
            :saving="saving"
            @save="notes => save(() => setEntryNotes(api, id, notes))"
          />
        </section>

        <section v-if="entry.kanji_readings.length" aria-labelledby="spellings" class="space-y-2">
          <h2 id="spellings" class="text-sm font-semibold uppercase tracking-wide text-muted">Escrituras</h2>
          <USwitch
            v-for="spelling in entry.kanji_readings"
            :key="spelling.id"
            :model-value="spelling.enabled"
            :disabled="saving"
            :label="spelling.kanji"
            :ui="{ label: 'font-japanese' }"
            @update:model-value="toggle('kanji-readings', spelling.id, $event)"
          />
        </section>

        <section aria-labelledby="readings" class="space-y-2">
          <h2 id="readings" class="text-sm font-semibold uppercase tracking-wide text-muted">Lecturas</h2>
          <USwitch
            v-for="reading in entry.readings"
            :key="reading.id"
            :model-value="reading.enabled"
            :disabled="saving"
            :label="reading.text"
            :ui="{ label: 'font-japanese' }"
            @update:model-value="toggle('readings', reading.id, $event)"
          />
        </section>

        <ItemCollections kind="entries" :item-id="entry.id" />
      </aside>
    </div>
  </AppPanel>
</template>
