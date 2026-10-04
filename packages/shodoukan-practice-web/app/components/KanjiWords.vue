<script setup lang="ts">
import type { Entry } from 'shodoukan-ui'
import { getDictionaryKanjiEntries } from '~/services/dictionary'

// A few dictionary words that use a kanji, for the side of a library kanji.
// Imported ones open the user's copy; the full list is on the dictionary's
// kanji page (a dictionary search would only find words starting with it).

const SHOWN = 5

const props = defineProps<{ literal: string }>()

const api = useApi()
const { glossCode } = useMeaningLang()
const status = useImportStatus()

const { data: words } = useAsyncData(
  () => `kanji-words-${props.literal}`,
  async () => {
    const page = await getDictionaryKanjiEntries(api, props.literal, SHOWN)
    await status.refresh(page.items.map(e => e.id), [])
    return page
  },
  { watch: [() => props.literal] },
)

/** The spelling with this kanji (a word may have others without it). */
function headword(entry: Entry): string {
  const spelling = entry.kanji_readings.find(k => k.kanji.includes(props.literal)) ?? entry.kanji_readings[0]
  return spelling?.kanji ?? entry.readings[0]?.text ?? ''
}

function meaning(entry: Entry): string {
  for (const sense of entry.senses) {
    const gloss = sense.glosses.find(g => g.lang === glossCode.value)
    if (gloss) return gloss.text
  }
  return ''
}

function link(entry: Entry): string {
  const practiceId = status.entries.value.get(entry.id)
  return practiceId === undefined ? `/dictionary/entries/${entry.id}` : `/library/entries/${practiceId}`
}
</script>

<template>
  <section v-if="words?.items.length" aria-labelledby="kanji-words" class="space-y-2">
    <h2 id="kanji-words" class="text-sm font-semibold uppercase tracking-wide text-muted">
      Palabras con {{ literal }}
    </h2>
    <ul class="divide-y divide-default rounded-md ring ring-default">
      <li v-for="entry in words.items" :key="entry.id">
        <NuxtLink :to="link(entry)" class="flex items-center gap-3 px-3 py-2 transition hover:bg-elevated">
          <div class="min-w-0 flex-1">
            <p class="truncate">
              <span class="font-japanese font-bold text-highlighted">{{ headword(entry) }}</span>
              <span v-if="entry.kanji_readings.length" class="ms-2 font-japanese text-xs text-muted">{{ entry.readings[0]?.text }}</span>
            </p>
            <p class="line-clamp-1 text-sm text-toned">{{ meaning(entry) || '—' }}</p>
          </div>
          <UIcon
            v-if="status.entries.value.has(entry.id)"
            name="i-lucide-check"
            class="size-4 shrink-0 text-success"
            aria-label="En tu librería"
          />
        </NuxtLink>
      </li>
    </ul>
    <ULink
      v-if="words.total > SHOWN"
      :to="`/dictionary/kanji/${literal}`"
      class="inline-flex items-center gap-1 text-sm text-primary"
    >
      Ver las {{ words.total }} palabras en el diccionario
      <UIcon name="i-lucide-arrow-right" class="size-4" />
    </ULink>
  </section>
</template>
