<script setup lang="ts">
import { KanjiStrokeAnimator } from 'shodoukan-ui'
import ConfirmModal from '~/components/ConfirmModal.vue'
import type { PracticeKanji, PracticeReadingItem } from '~/models/practice'
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
const { lang, options: languages } = useMeaningLang()
const back = useBackLink('kanji')

const id = computed(() => Number(route.params.id))
const { item: kanji, status, saving, save } = useEditableItem<PracticeKanji>(
  () => `library-kanji-${id.value}`,
  () => getLibraryKanji(api, id.value),
)

const languageLabel = computed(() => languages.find(l => l.value === lang.value)?.label ?? lang.value)
const meanings = computed(() => kanji.value?.meanings.filter(m => m.lang === lang.value) ?? [])

const readingGroups = computed<{ label: string; items: PracticeReadingItem[] }[]>(() => {
  if (!kanji.value) return []
  return [
    { label: 'On\'yomi', items: kanji.value.on_readings },
    { label: 'Kun\'yomi', items: kanji.value.kun_readings },
    { label: 'Nanori', items: kanji.value.nanori },
  ].filter(group => group.items.length)
})

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
        <header class="flex flex-wrap items-center gap-6">
          <span class="font-japanese text-8xl leading-none font-bold text-highlighted">{{ kanji.literal }}</span>
          <dl class="flex flex-wrap gap-4 text-sm">
            <div>
              <dt class="text-xs uppercase tracking-wide text-dimmed">Trazos</dt>
              <dd class="text-toned">{{ kanji.stroke_count }}</dd>
            </div>
            <div v-if="kanji.grade">
              <dt class="text-xs uppercase tracking-wide text-dimmed">Grado</dt>
              <dd class="text-toned">{{ kanji.grade }}</dd>
            </div>
            <div v-if="kanji.jlpt">
              <dt class="text-xs uppercase tracking-wide text-dimmed">JLPT</dt>
              <dd class="text-toned">N{{ kanji.jlpt }}</dd>
            </div>
          </dl>
        </header>

        <section aria-labelledby="meanings" class="space-y-3">
          <div class="flex items-baseline justify-between gap-2">
            <h2 id="meanings" class="text-sm font-semibold uppercase tracking-wide text-muted">Significados</h2>
            <span class="text-xs text-dimmed">en {{ languageLabel }} · cámbialo en el menú lateral</span>
          </div>
          <UCard>
            <MeaningList
              :meanings="meanings"
              :disabled="saving"
              @toggle="(meaningId, enabled) => save(() => setKanjiPartEnabled(api, id, 'meanings', meaningId, enabled))"
              @add="text => save(() => addKanjiMeaning(api, id, text, lang))"
              @edit="(meaningId, text) => save(() => editKanjiMeaning(api, id, meaningId, text))"
              @remove="meaningId => save(() => removeKanjiMeaning(api, id, meaningId))"
            />
          </UCard>
        </section>

        <section aria-labelledby="readings" class="space-y-3">
          <h2 id="readings" class="text-sm font-semibold uppercase tracking-wide text-muted">Lecturas</h2>
          <div v-for="group in readingGroups" :key="group.label" class="flex items-start gap-3">
            <span class="w-20 shrink-0 pt-1.5 text-xs uppercase tracking-wide text-dimmed">{{ group.label }}</span>
            <ReadingChips
              :readings="group.items"
              :disabled="saving"
              @toggle="(readingId, enabled) => save(() => setKanjiPartEnabled(api, id, 'readings', readingId, enabled))"
            />
          </div>
        </section>

        <section aria-labelledby="strokes" class="space-y-3">
          <h2 id="strokes" class="text-sm font-semibold uppercase tracking-wide text-muted">Orden de trazos</h2>
          <KanjiStrokeAnimator :key="kanji.literal" :literal="kanji.literal" play-label="Reproducir" playing-label="Reproduciendo…" />
        </section>
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

        <section aria-labelledby="collections" class="space-y-2">
          <h2 id="collections" class="text-sm font-semibold uppercase tracking-wide text-muted">Colecciones</h2>
          <ItemCollections kind="kanji" :item-id="kanji.id" />
        </section>
      </aside>
    </div>
  </AppPanel>
</template>
