<script setup lang="ts">
import { getEntry, getEntryKanji } from '~/services/entries'
import type { Entry, EntryKanjiLink, Sense, ExampleSentence } from '~/models/entry'
import { glossLang } from '~/models/kanji'
import { shortenPos } from '~/utils/pos'

definePageMeta({ layout: 'dictionary' })

const config = useRuntimeConfig()
const route = useRoute()

const id = computed(() => Number(route.params.id))
const lang = computed(() => (route.query.lang as string) ?? 'en')
const langCode = computed(() => glossLang(lang.value))

const entry = ref<Entry | null>(null)
const kanjiLinks = ref<EntryKanjiLink[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const primaryForm = computed(() =>
  entry.value?.kanji_readings[0]?.kanji ?? entry.value?.readings[0]?.text ?? '',
)

const reading = computed(() =>
  entry.value?.kanji_readings.length ? (entry.value?.readings[0]?.text ?? '') : '',
)

const allForms = computed(() =>
  entry.value?.kanji_readings.map(r => r.kanji) ?? [],
)

const allReadings = computed(() =>
  entry.value?.readings.map(r => r.text) ?? [],
)

const filteredSenses = computed(() =>
  entry.value?.senses.filter(s => s.glosses.some(g => g.lang === langCode.value)) ?? [],
)

function glossesFor(sense: Sense): string {
  return sense.glosses
    .filter(g => g.lang === langCode.value)
    .map(g => g.text)
    .join(' · ')
}

function japaneseSentence(sentences: ExampleSentence[]): string {
  return sentences.find(s => s.lang === 'jpn')?.text ?? ''
}

function targetSentence(sentences: ExampleSentence[]): string {
  return sentences.find(s => s.lang === langCode.value)?.text ?? ''
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const [e, kl] = await Promise.all([
      getEntry(id.value, config.public.apiBase),
      getEntryKanji(id.value, config.public.apiBase),
    ])
    entry.value = e
    kanjiLinks.value = kl
  }
  catch {
    error.value = 'Could not load entry.'
  }
  finally {
    loading.value = false
  }
}

watch(id, load, { immediate: true })
</script>

<template>
  <main class="mx-auto w-[80%] max-w-3xl px-4 py-10">
    <div v-if="loading" class="py-12 text-center text-zinc-500">
      Loading…
    </div>

    <div v-else-if="error" class="py-12 text-center text-red-400">
      {{ error }}
    </div>

    <template v-else-if="entry">
      <!-- Headword + reading -->
      <div class="mb-4">
        <div
          v-if="reading"
          class="mb-0.5 font-japanese text-sm text-zinc-400"
        >
          {{ reading }}
        </div>
        <h1 class="font-japanese text-4xl font-bold text-zinc-100">
          {{ primaryForm }}
        </h1>
      </div>

      <!-- Badges -->
      <div class="mb-4 flex flex-wrap gap-2">
        <span
          v-if="entry.jlpt"
          class="min-w-max rounded bg-indigo-600/30 px-2 py-0.5 text-xs font-medium text-indigo-300"
        >JLPT N{{ entry.jlpt }}</span>
        <span
          v-if="entry.is_common"
          class="min-w-max rounded bg-teal-600/30 px-2 py-0.5 text-xs font-medium text-teal-300"
        >common</span>
      </div>

      <!-- All forms + readings if multiple -->
      <div v-if="allForms.length > 1 || allReadings.length > 1" class="mb-5 flex flex-wrap gap-4 text-sm text-zinc-400">
        <div v-if="allForms.length > 1">
          <span class="text-xs uppercase tracking-wide text-zinc-600">Forms&nbsp;</span>
          <span class="font-japanese">{{ allForms.join('、') }}</span>
        </div>
        <div v-if="allReadings.length > 1">
          <span class="text-xs uppercase tracking-wide text-zinc-600">Readings&nbsp;</span>
          <span class="font-japanese">{{ allReadings.join('、') }}</span>
        </div>
      </div>

      <!-- Kanji chips -->
      <div v-if="kanjiLinks.length" class="mb-6 flex flex-wrap gap-2">
        <span class="self-center text-xs uppercase tracking-wide text-zinc-500">Kanji</span>
        <NuxtLink
          v-for="kl in kanjiLinks"
          :key="kl.literal"
          :to="`/kanji/${kl.literal}`"
          class="rounded border border-zinc-700 bg-zinc-800 px-2 py-0.5 font-japanese text-sm text-zinc-200 transition hover:border-zinc-500 hover:bg-zinc-700"
        >
          {{ kl.literal }}
        </NuxtLink>
      </div>

      <!-- Senses -->
      <ol class="mb-6 flex flex-col gap-5">
        <li
          v-for="(sense, i) in filteredSenses"
          :key="sense.id"
          class="flex flex-col gap-1.5"
        >
          <div class="flex flex-wrap items-center gap-1.5">
            <span class="shrink-0 text-sm text-zinc-500">{{ i + 1 }}.</span>
            <span
              v-for="pos in sense.pos"
              :key="pos"
              class="min-w-max rounded bg-zinc-700 px-1.5 py-0.5 text-xs text-zinc-400"
            >{{ shortenPos(pos) }}</span>
          </div>

          <p class="text-zinc-100">
            {{ glossesFor(sense) }}
          </p>

          <p
            v-if="[...sense.misc, ...sense.info].length"
            class="text-xs italic text-zinc-500"
          >
            {{ [...sense.misc, ...sense.info].join(' · ') }}
          </p>

          <!-- Examples -->
          <div
            v-if="sense.examples.length"
            class="mt-1 flex flex-col gap-2 border-l-2 border-zinc-700 pl-3"
          >
            <div
              v-for="ex in sense.examples"
              :key="ex.id"
              class="flex flex-col gap-0.5"
            >
              <span class="font-japanese text-sm text-zinc-200">{{ japaneseSentence(ex.sentences) }}</span>
              <span
                v-if="targetSentence(ex.sentences)"
                class="text-sm text-zinc-400"
              >{{ targetSentence(ex.sentences) }}</span>
            </div>
          </div>

          <!-- Cross-references -->
          <p
            v-if="sense.cross_references.length"
            class="text-xs text-zinc-500"
          >
            See also:
            <span
              v-for="(ref, ri) in sense.cross_references"
              :key="ri"
            >{{ ref.reference }}<span v-if="ri < sense.cross_references.length - 1">, </span></span>
          </p>
        </li>
      </ol>
    </template>
  </main>
</template>
