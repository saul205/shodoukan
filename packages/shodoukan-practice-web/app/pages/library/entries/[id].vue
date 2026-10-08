<script setup lang="ts">
import ConfirmModal from '~/components/ConfirmModal.vue'
import type { EntryPart, PracticeEntry } from '~/models/practice'
import {
  addExample,
  addGloss,
  addReading,
  addSpelling,
  addSense,
  editExample,
  editGloss,
  getLibraryEntry,
  removeExample,
  removeGloss,
  removeLibraryEntry,
  removeReading,
  removeSpelling,
  removeSense,
  setEntryActive,
  setEntryNotes,
  setEntryPartEnabled,
  setSenseNotes,
} from '~/services/library'
import { getDictionaryEntryKanji, getDictionaryKanji } from '~/services/dictionary'
import { kanjiIn } from '~/utils/own-entry'
import { entryHeadword } from '~/utils/practice-text'
import { entryWriting } from '~/utils/writing-practice'

// A word of the library and its customisation. The same page opens from the
// library and from a collection (`?collection=<id>`, for the back link).
// Every change is saved as it's made.

const route = useRoute()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()
const { glossCode } = useMeaningLang()
const back = useBackLink('entries')

const id = computed(() => Number(route.params.id))
const { item: entry, status, saving, save } = useEditableItem<PracticeEntry>(
  () => `library-entry-${id.value}`,
  () => getLibraryEntry(api, id.value),
)

// The word's kanji come from the dictionary, with whether each one is imported:
// the dictionary entry's, or for a word of the user's own, those of its first
// spelling (the ones the dictionary has).
// How it's written, for practising it: what's enabled, like everywhere else.
const writing = computed(() => (entry.value ? entryWriting(entry.value) : null))

const kanjiStatus = useImportStatus()
const sourceId = computed(() => entry.value?.source_entry_id)
const ownLiterals = computed(() =>
  entry.value && entry.value.source_entry_id === null ? kanjiIn(entry.value.kanji_readings[0]?.kanji ?? '') : [],
)
// Watched as a string: every edit replaces `entry`, so `ownLiterals` is a new
// array each time, and Vue compares arrays by reference; the string only
// changes when the kanji do, so edits don't fetch the list again.
const ownLiteralsKey = computed(() => ownLiterals.value.join(''))
const { data: wordKanji } = useAsyncData(
  () => `library-entry-kanji-${sourceId.value}-${ownLiteralsKey.value}`,
  async () => {
    if (sourceId.value === undefined) return null
    const kanji = sourceId.value === null
      ? (await Promise.allSettled(ownLiterals.value.map(literal => getDictionaryKanji(api, literal))))
          .flatMap(result => (result.status === 'fulfilled' ? [result.value] : []))
      : await getDictionaryEntryKanji(api, sourceId.value)
    await kanjiStatus.refresh([], kanji.map(k => k.literal))
    return kanji
  },
  { watch: [sourceId, ownLiteralsKey] },
)

const spellings = computed(() => entry.value?.kanji_readings.map(k => ({ ...k, text: k.kanji })) ?? [])

const toggle = (part: EntryPart, itemId: number, enabled: boolean) =>
  save(() => setEntryPartEnabled(api, id.value, part, itemId, enabled))

// An own sense goes with its meanings, examples and note, so it asks first.
async function deleteSense(senseId: number) {
  const confirmed = await overlay.create(ConfirmModal).open({
    title: '¿Eliminar este significado?',
    description: 'Se borran sus significados, ejemplos y nota propios.',
    confirmLabel: 'Eliminar',
  }).result
  if (confirmed) await save(() => removeSense(api, id.value, senseId))
}

async function remove() {
  // A word of the user's own isn't in the dictionary: removing it loses it.
  const own = entry.value?.source_entry_id === null
  const confirmed = await overlay.create(ConfirmModal).open({
    title: '¿Quitar de tu librería?',
    description: own
      ? 'Es una palabra tuya: se borra entera y sale de todas tus colecciones. No se puede recuperar.'
      : 'Se borran tus notas y significados propios, y sale de todas tus colecciones. Podrás volver a importarla desde el diccionario.',
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
        v-if="writing"
        :to="{ path: '/practice/play', query: { entries: entry.id, from: route.fullPath } }"
        icon="i-lucide-pen-line"
        label="Practicar escritura"
        color="neutral"
        variant="outline"
        data-testid="practice-entry"
      />
      <UButton
        v-if="entry.source_entry_id !== null"
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
        <EntryDetail
          :entry="entry"
          :saving="saving"
          @toggle="toggle"
          @add-sense="text => save(() => addSense(api, id, text, glossCode))"
          @remove-sense="deleteSense"
          @add-gloss="(senseId, text) => save(() => addGloss(api, id, senseId, text, glossCode))"
          @edit-gloss="(glossId, text) => save(() => editGloss(api, id, glossId, text))"
          @remove-gloss="glossId => save(() => removeGloss(api, id, glossId))"
          @add-example="(senseId, japanese, translation) => save(() => addExample(api, id, senseId, japanese, translation, glossCode))"
          @edit-example="(exampleId, japanese, translation) => save(() => editExample(api, id, exampleId, japanese, translation, glossCode))"
          @remove-example="exampleId => save(() => removeExample(api, id, exampleId))"
          @sense-notes="(senseId, notes) => save(() => setSenseNotes(api, id, senseId, notes))"
        />

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

        <section aria-labelledby="spellings" class="space-y-2">
          <h2 id="spellings" class="text-sm font-semibold uppercase tracking-wide text-muted">Escrituras</h2>
          <FormList
            :items="spellings"
            add-label="Añadir una escritura…"
            :disabled="saving"
            @toggle="(spellingId, enabled) => toggle('kanji-readings', spellingId, enabled)"
            @add="kanji => save(() => addSpelling(api, id, kanji))"
            @remove="spellingId => save(() => removeSpelling(api, id, spellingId))"
          />
        </section>

        <section aria-labelledby="readings" class="space-y-2">
          <h2 id="readings" class="text-sm font-semibold uppercase tracking-wide text-muted">Lecturas</h2>
          <FormList
            :items="entry.readings"
            add-label="Añadir una lectura en kana…"
            kana
            :disabled="saving"
            @toggle="(readingId, enabled) => toggle('readings', readingId, enabled)"
            @add="text => save(() => addReading(api, id, text))"
            @remove="readingId => save(() => removeReading(api, id, readingId))"
          />
        </section>

        <ItemCollections kind="entries" :item-id="entry.id" />
      </aside>
    </div>
  </AppPanel>
</template>
