<script setup lang="ts">
import { KanjiCardCompact, shortenPos } from 'shodoukan-ui'
import { NuxtLink } from '#components'
import { getDictionaryEntry, getDictionaryEntryKanji } from '~/services/dictionary'
import { japaneseSentence, translatedSentence } from '~/utils/sentences'

// A dictionary entry in full, with its kanji, ready to import.

const route = useRoute()
const api = useApi()
const { lang, glossCode } = useMeaningLang()
const status = useImportStatus()

const id = computed(() => Number(route.params.id))

const { data, status: loading, error } = useAsyncData(
  () => `dictionary-entry-${id.value}`,
  async () => {
    const [entry, kanji] = await Promise.all([
      getDictionaryEntry(api, id.value),
      getDictionaryEntryKanji(api, id.value),
    ])
    await status.refresh([entry.id], kanji.map(k => k.literal))
    return { entry, kanji }
  },
  { watch: [id] },
)

const headword = computed(() => {
  const entry = data.value?.entry
  return entry?.kanji_readings[0]?.kanji ?? entry?.readings[0]?.text ?? ''
})
const reading = computed(() => (data.value?.entry.kanji_readings.length ? data.value.entry.readings[0]?.text : ''))
const otherForms = computed(() => data.value?.entry.kanji_readings.slice(1).map(k => k.kanji) ?? [])
const otherReadings = computed(() => data.value?.entry.readings.slice(1).map(r => r.text) ?? [])

/** The word's kanji not yet in the library, for "import the missing ones". */
const missingKanji = computed(() =>
  (data.value?.kanji ?? []).map(k => k.literal).filter(literal => !status.kanji.value.has(literal)),
)

const senses = computed(() =>
  (data.value?.entry.senses ?? [])
    .map(sense => ({ sense, glosses: sense.glosses.filter(g => g.lang === glossCode.value).map(g => g.text) }))
    .filter(s => s.glosses.length),
)
</script>

<template>
  <AppPanel :title="headword || 'Palabra'">
    <template #leading>
      <UButton icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver" @click="$router.back()" />
    </template>

    <div v-if="loading === 'pending' && !data" class="space-y-3">
      <USkeleton class="h-16 w-48" />
      <USkeleton v-for="i in 3" :key="i" class="h-12 w-full" />
    </div>

    <UEmpty
      v-else-if="error || !data"
      icon="i-lucide-search-x"
      title="No se ha encontrado esta palabra"
      :actions="[{ label: 'Volver al diccionario', to: '/dictionary', icon: 'i-lucide-arrow-left' }]"
    />

    <div v-else class="space-y-6">
      <header class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p v-if="reading" class="font-japanese text-sm text-muted">{{ reading }}</p>
          <h1 class="font-japanese text-4xl font-bold text-highlighted">{{ headword }}</h1>
          <div class="mt-2 flex flex-wrap gap-1">
            <UBadge v-if="data.entry.jlpt" :label="`JLPT N${data.entry.jlpt}`" variant="soft" />
            <UBadge v-if="data.entry.is_common" label="común" color="success" variant="soft" />
          </div>
        </div>
        <div class="flex items-center gap-2">
          <UButton
            v-if="status.entries.value.has(data.entry.id)"
            :to="`/library/entries/${status.entries.value.get(data.entry.id)}`"
            label="Abrir en tu librería"
            icon="i-lucide-arrow-up-right"
            color="neutral"
            variant="ghost"
            size="sm"
          />
          <UFieldGroup>
            <ImportButton
              :imported="status.entries.value.has(data.entry.id)"
              :loading="status.isBusyEntry(data.entry.id)"
              @import="status.addEntry(data.entry.id)"
              @remove="status.removeEntry(data.entry.id)"
            />
            <CollectionMenuButton
              kind="entries"
              :practice-id="status.entries.value.get(data.entry.id)"
              :loading="status.isBusyEntry(data.entry.id)"
              @import="status.addEntry(data.entry.id, $event)"
            />
          </UFieldGroup>
        </div>
      </header>

      <dl v-if="otherForms.length || otherReadings.length" class="flex flex-wrap gap-6 text-sm">
        <div v-if="otherForms.length">
          <dt class="text-xs uppercase tracking-wide text-dimmed">Otras formas</dt>
          <dd class="font-japanese text-toned">{{ otherForms.join('、') }}</dd>
        </div>
        <div v-if="otherReadings.length">
          <dt class="text-xs uppercase tracking-wide text-dimmed">Otras lecturas</dt>
          <dd class="font-japanese text-toned">{{ otherReadings.join('、') }}</dd>
        </div>
      </dl>

      <section aria-labelledby="meanings">
        <h2 id="meanings" class="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">Significados</h2>
        <p v-if="!senses.length" class="text-sm text-muted">No hay significados en este idioma.</p>
        <ol class="space-y-5">
          <li v-for="({ sense, glosses }, i) in senses" :key="i" class="space-y-1.5">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="text-sm text-dimmed">{{ i + 1 }}.</span>
              <UBadge v-for="pos in sense.pos" :key="pos" :label="shortenPos(pos)" color="neutral" variant="subtle" size="sm" />
            </div>
            <p class="text-default">{{ glosses.join(' · ') }}</p>
            <p v-if="sense.misc.length || sense.info.length" class="text-xs text-muted italic">
              {{ [...sense.misc, ...sense.info].join(' · ') }}
            </p>
            <div v-if="sense.examples.length" class="space-y-2 border-s-2 border-default ps-3">
              <div v-for="(example, j) in sense.examples" :key="j">
                <p class="font-japanese text-sm text-default">{{ japaneseSentence(example.sentences) }}</p>
                <p v-if="translatedSentence(example.sentences, glossCode)" class="text-sm text-muted">
                  {{ translatedSentence(example.sentences, glossCode) }}
                </p>
              </div>
            </div>
            <p v-if="sense.cross_references.length" class="text-xs text-muted">
              Ver también: {{ sense.cross_references.map(r => r.reference).join(', ') }}
            </p>
          </li>
        </ol>
      </section>

      <section v-if="data.kanji.length" aria-labelledby="kanji">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 id="kanji" class="text-sm font-semibold uppercase tracking-wide text-muted">Kanji</h2>
          <UButton
            v-if="missingKanji.length > 1"
            :label="`Importar los ${missingKanji.length} que faltan`"
            icon="i-lucide-plus"
            variant="soft"
            size="sm"
            :loading="missingKanji.some(literal => status.isBusyKanji(literal))"
            @click="status.addKanjiList(missingKanji)"
          />
        </div>
        <!-- Same as the search results: the import button sits over each card's
             corner, beside the card's link rather than inside it. -->
        <div class="flex flex-wrap gap-3">
          <div v-for="k in data.kanji" :key="k.literal" class="relative flex flex-1">
            <KanjiCardCompact
              :kanji="k"
              :lang="lang"
              :link-component="NuxtLink"
              :href="`/dictionary/kanji/${k.literal}`"
            />
            <UFieldGroup class="absolute top-2 right-2">
              <ImportButton
                icon-only
                :imported="status.kanji.value.has(k.literal)"
                :loading="status.isBusyKanji(k.literal)"
                @import="status.addKanji(k.literal)"
                @remove="status.removeKanji(k.literal)"
              />
              <CollectionMenuButton
                kind="kanji"
                icon-only
                :practice-id="status.kanji.value.get(k.literal)"
                :loading="status.isBusyKanji(k.literal)"
                @import="status.addKanji(k.literal, $event)"
              />
            </UFieldGroup>
          </div>
        </div>
      </section>
    </div>
  </AppPanel>
</template>
