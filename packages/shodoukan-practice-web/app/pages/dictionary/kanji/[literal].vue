<script setup lang="ts">
import { EntryCard } from 'shodoukan-ui'
import { NuxtLink } from '#components'
import { getDictionaryKanji, getDictionaryKanjiEntries } from '~/services/dictionary'

// A dictionary kanji: readings, meanings, stroke order and the words that
// use it, like the dictionary web's kanji page.

const WORDS_PAGE_SIZE = 10

const route = useRoute()
const api = useApi()
const { lang } = useMeaningLang()
const status = useImportStatus()

const literal = computed(() => String(route.params.literal))
const wordsPage = ref(1)

const { data: kanji, status: loading, error } = useAsyncData(
  () => `dictionary-kanji-${literal.value}`,
  async () => {
    const found = await getDictionaryKanji(api, literal.value)
    await status.refresh([], [found.literal])
    return found
  },
  { watch: [literal] },
)

const { data: words } = useAsyncData(
  () => `dictionary-kanji-words-${literal.value}-${wordsPage.value}`,
  () => getDictionaryKanjiEntries(api, literal.value, WORDS_PAGE_SIZE, (wordsPage.value - 1) * WORDS_PAGE_SIZE),
  { watch: [literal, wordsPage] },
)

const meanings = computed(() => kanji.value?.meanings.filter(m => m.lang === lang.value).map(m => m.text) ?? [])

const readingGroups = computed(() => {
  if (!kanji.value) return []
  return [
    { label: 'Kun\'yomi', readings: kanji.value.kun_readings, search: (r: string) => r.replace('.', '').replace('-', '') },
    { label: 'On\'yomi', readings: kanji.value.on_readings, search: (r: string) => r },
    { label: 'Nanori', readings: kanji.value.nanori, search: (r: string) => r },
  ].filter(group => group.readings.length)
})

const stats = computed(() => {
  if (!kanji.value) return []
  return [
    { label: 'Trazos', value: kanji.value.stroke_count },
    { label: 'Grado', value: kanji.value.grade },
    { label: 'JLPT', value: kanji.value.jlpt ? `N${kanji.value.jlpt}` : null },
    { label: 'Frecuencia', value: kanji.value.freq },
  ].filter(stat => stat.value !== null)
})
</script>

<template>
  <AppPanel :title="`Kanji ${literal}`">
    <template #leading>
      <UButton icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver" @click="$router.back()" />
    </template>

    <div v-if="loading === 'pending' && !kanji" class="space-y-3">
      <USkeleton class="size-24" />
      <USkeleton v-for="i in 3" :key="i" class="h-10 w-full" />
    </div>

    <UEmpty
      v-else-if="error || !kanji"
      icon="i-lucide-search-x"
      title="No se ha encontrado este kanji"
      :actions="[{ label: 'Volver al diccionario', to: '/dictionary', icon: 'i-lucide-arrow-left' }]"
    />

    <div v-else class="space-y-8">
      <!-- The meanings grow to fill the kanji's height, with the data at its base. -->
      <header class="flex flex-wrap items-start gap-6">
        <span class="font-japanese text-8xl leading-none font-bold text-highlighted">{{ kanji.literal }}</span>
        <div class="flex min-w-0 flex-1 flex-col justify-between gap-3 self-stretch">
          <p class="text-2xl leading-snug text-highlighted sm:text-3xl">{{ meanings.join(' · ') || 'Sin significados en este idioma.' }}</p>
          <dl class="flex flex-wrap gap-4 text-sm">
            <div v-for="stat in stats" :key="stat.label">
              <dt class="text-xs uppercase tracking-wide text-dimmed">{{ stat.label }}</dt>
              <dd class="text-toned">{{ stat.value }}</dd>
            </div>
          </dl>
        </div>
        <div class="flex w-full flex-wrap items-center justify-center gap-2 sm:w-auto sm:self-start">
          <UButton
            v-if="status.kanji.value.has(kanji.literal)"
            :to="`/library/kanji/${status.kanji.value.get(kanji.literal)}`"
            label="Abrir en tu librería"
            icon="i-lucide-arrow-up-right"
            color="neutral"
            variant="ghost"
            size="sm"
          />
          <UFieldGroup>
            <ImportButton
              :imported="status.kanji.value.has(kanji.literal)"
              :loading="status.isBusyKanji(kanji.literal)"
              @import="status.addKanji(kanji.literal)"
              @remove="status.removeKanji(kanji.literal)"
            />
            <CollectionMenuButton
              kind="kanji"
              :practice-id="status.kanji.value.get(kanji.literal)"
              :loading="status.isBusyKanji(kanji.literal)"
              @import="status.addKanji(kanji.literal, $event)"
            />
          </UFieldGroup>
        </div>
      </header>

      <section class="space-y-2" aria-label="Lecturas">
        <div v-for="group in readingGroups" :key="group.label" class="flex flex-wrap items-center gap-2">
          <span class="w-20 text-xs uppercase tracking-wide text-dimmed">{{ group.label }}</span>
          <UButton
            v-for="r in group.readings"
            :key="r"
            :label="r"
            :to="{ path: '/dictionary', query: { q: group.search(r) } }"
            color="neutral"
            variant="subtle"
            size="sm"
            class="font-japanese"
          />
        </div>
      </section>

      <section aria-labelledby="strokes" class="space-y-3">
        <h2 id="strokes" class="text-sm font-semibold uppercase tracking-wide text-muted">Orden de trazos</h2>
        <KanjiStrokeOrder :literal="kanji.literal" />
      </section>

      <section v-if="words?.items.length" aria-labelledby="words" class="space-y-3">
        <h2 id="words" class="text-sm font-semibold uppercase tracking-wide text-muted">
          Palabras con {{ kanji.literal }} <span class="font-normal">({{ words.total }})</span>
        </h2>
        <EntryCard
          v-for="entry in words.items"
          :key="entry.id"
          :entry="entry"
          :lang="lang"
          :link-component="NuxtLink"
          :details-href="`/dictionary/entries/${entry.id}`"
          details-label="detalles →"
        />
        <UPagination
          v-if="words.total > WORDS_PAGE_SIZE"
          v-model:page="wordsPage"
          :total="words.total"
          :items-per-page="WORDS_PAGE_SIZE"
          class="flex justify-center"
        />
      </section>
    </div>
  </AppPanel>
</template>
