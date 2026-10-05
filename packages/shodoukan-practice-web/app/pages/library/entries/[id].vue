<script setup lang="ts">
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
import { entryHeadword } from '~/utils/practice-text'

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
        <EntryDetail
          :entry="entry"
          :saving="saving"
          @toggle="toggle"
          @add-gloss="(senseId, text) => save(() => addGloss(api, id, senseId, text, glossCode))"
          @edit-gloss="(glossId, text) => save(() => editGloss(api, id, glossId, text))"
          @remove-gloss="glossId => save(() => removeGloss(api, id, glossId))"
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
