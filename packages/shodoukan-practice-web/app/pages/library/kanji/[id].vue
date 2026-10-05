<script setup lang="ts">
import ConfirmModal from '~/components/ConfirmModal.vue'
import type { PracticeKanji } from '~/models/practice'
import {
  addKanjiMeaning,
  editKanjiMeaning,
  getLibraryKanji,
  removeKanjiMeaning,
  removeLibraryKanji,
  setKanjiActive,
  setKanjiNotes,
  setKanjiPartEnabled,
} from '~/services/library'

// A kanji of the library and its customisation; shared by the library and
// collections (`?collection=<id>` for the back link). Saves as it changes.

const route = useRoute()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()
const { lang } = useMeaningLang()
const back = useBackLink('kanji')

const id = computed(() => Number(route.params.id))
const { item: kanji, status, saving, save } = useEditableItem<PracticeKanji>(
  () => `library-kanji-${id.value}`,
  () => getLibraryKanji(api, id.value),
)

async function remove() {
  const confirmed = await overlay.create(ConfirmModal).open({
    title: '¿Quitar de tu librería?',
    description: 'Se borran tus notas y significados propios, y sale de todas tus colecciones. Podrás volver a importarlo desde el diccionario.',
    confirmLabel: 'Quitar',
  }).result
  if (!confirmed) return
  try {
    await removeLibraryKanji(api, id.value)
    notify.success('Quitado de tu librería')
    await navigateTo(back.value.to)
  }
  catch (error) {
    notify.failure(error, 'No se ha podido quitar')
  }
}
</script>

<template>
  <AppPanel :title="kanji ? `Kanji ${kanji.literal}` : 'Kanji'">
    <template #leading>
      <UButton :to="back.to" icon="i-lucide-arrow-left" color="neutral" variant="ghost" :aria-label="back.label" />
    </template>
    <template v-if="kanji" #actions>
      <UButton
        :to="`/dictionary/kanji/${kanji.literal}`"
        icon="i-lucide-book-open"
        label="Abrir en el diccionario"
        color="neutral"
        variant="ghost"
        class="hidden sm:inline-flex"
      />
      <UButton icon="i-lucide-trash-2" label="Quitar" color="error" variant="soft" @click="remove" />
    </template>

    <div v-if="status === 'pending' && !kanji" class="space-y-3">
      <USkeleton class="size-24" />
      <USkeleton v-for="i in 3" :key="i" class="h-16 w-full" />
    </div>

    <UEmpty
      v-else-if="!kanji"
      icon="i-lucide-search-x"
      title="Este kanji no está en tu librería"
      :actions="[{ label: back.label, to: back.to, icon: 'i-lucide-arrow-left' }]"
    />

    <div v-else class="grid gap-8 lg:grid-cols-3">
      <div class="space-y-8 lg:col-span-2">
        <KanjiDetail
          :kanji="kanji"
          :saving="saving"
          @toggle="(part, itemId, enabled) => save(() => setKanjiPartEnabled(api, id, part, itemId, enabled))"
          @add-meaning="text => save(() => addKanjiMeaning(api, id, text, lang))"
          @edit-meaning="(meaningId, text) => save(() => editKanjiMeaning(api, id, meaningId, text))"
          @remove-meaning="meaningId => save(() => removeKanjiMeaning(api, id, meaningId))"
        />
      </div>

      <aside class="space-y-6">
        <UCard>
          <USwitch
            :model-value="kanji.is_active"
            :disabled="saving"
            label="Activo para practicar"
            description="Los inactivos siguen en tu librería y colecciones, pero no se practican."
            @update:model-value="active => save(() => setKanjiActive(api, id, active))"
          />
        </UCard>

        <NotesEditor
          :notes="kanji.notes"
          label="Notas"
          placeholder="Radicales, mnemotecnias, palabras que lo usan…"
          :saving="saving"
          @save="notes => save(() => setKanjiNotes(api, id, notes))"
        />

        <ItemCollections kind="kanji" :item-id="kanji.id" />

        <KanjiWords :literal="kanji.literal" />
      </aside>
    </div>
  </AppPanel>
</template>
