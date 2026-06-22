<script setup lang="ts">
import { getKanji } from '~/services/kanji'
import { getEntriesForKanji } from '~/services/entries'
import type { Kanji } from '~/models/kanji'
import type { Entry } from '~/models/entry'
import { SUPPORTED_LANGUAGES } from '~/models/kanji'

definePageMeta({ layout: 'dictionary' })

const config = useRuntimeConfig()
const route = useRoute()

const literal = computed(() => route.params.literal as string)
const lang = computed(() => (route.query.lang as string) ?? 'en')

const kanji = ref<Kanji | null>(null)
const entries = ref<Entry[]>([])
const loading = ref(true)
const error = ref<string | null>(null)
const strokeError = ref(false)

const strokeOrderUrl = computed(() => {
  const cp = literal.value.codePointAt(0)
  if (!cp) return null
  return `https://raw.githack.com/KanjiVG/kanjivg/master/kanji/${cp.toString(16).padStart(5, '0')}.svg`
})

const meaningsByLang = computed<{ label: string; texts: string[] }[]>(() => {
  if (!kanji.value) return []
  const groups: Record<string, string[]> = {}
  for (const m of kanji.value.meanings) {
    if (!groups[m.lang]) groups[m.lang] = []
    groups[m.lang].push(m.text)
  }
  return Object.entries(groups).map(([code, texts]) => ({
    label: SUPPORTED_LANGUAGES.find(l => l.code === code)?.label ?? code.toUpperCase(),
    texts,
  }))
})

async function load() {
  loading.value = true
  error.value = null
  strokeError.value = false
  try {
    const [k, ep] = await Promise.all([
      getKanji(literal.value, config.public.apiBase),
      getEntriesForKanji(literal.value, config.public.apiBase, 10),
    ])
    kanji.value = k
    entries.value = ep.items
  }
  catch {
    error.value = 'Could not load kanji data.'
  }
  finally {
    loading.value = false
  }
}

watch(literal, load, { immediate: true })
</script>

<template>
  <main class="mx-auto w-[80%] px-4 py-10">
    <div v-if="loading" class="py-12 text-center text-zinc-500">
      Loading…
    </div>

    <div v-else-if="error" class="py-12 text-center text-red-400">
      {{ error }}
    </div>

    <template v-else-if="kanji">
      <!-- Header row: kanji + stroke visuals wrap together -->
      <div class="mb-4 flex flex-wrap items-start gap-20">
        <!-- Large kanji + badges -->
        <div class="flex flex-col items-center gap-3">
          <span class="font-japanese text-[8rem] leading-none text-zinc-100">{{ kanji.literal }}</span>
          <div class="flex flex-wrap justify-center gap-2">
            <span
              v-if="kanji.jlpt"
              :title="`Japanese Language Proficiency Test — N${kanji.jlpt} (N5 is easiest, N1 is hardest)`"
              class="min-w-max cursor-help rounded bg-indigo-600/30 px-2 py-0.5 text-xs font-medium text-indigo-300"
            >JLPT N{{ kanji.jlpt }}</span>
            <span
              v-if="kanji.grade"
              :title="`Taught in Japanese elementary school grade ${kanji.grade}`"
              class="min-w-max cursor-help rounded bg-zinc-700 px-2 py-0.5 text-xs text-zinc-400"
            >Grade {{ kanji.grade }}</span>
            <span
              title="Number of brush strokes required to write this character"
              class="min-w-max cursor-help rounded bg-zinc-700 px-2 py-0.5 text-xs text-zinc-400"
            >{{ kanji.stroke_count }} strokes</span>
            <span
              v-if="kanji.freq"
              :title="`Frequency rank #${kanji.freq} among commonly used kanji — lower means more common`"
              class="min-w-max cursor-help rounded bg-zinc-700 px-2 py-0.5 text-xs text-zinc-400"
            >Freq #{{ kanji.freq }}</span>
          </div>
        </div>

        <!-- Diagram + Animated: sit to the right of the kanji, wrap as a pair -->
        <div class="flex flex-1 flex-wrap items-start justify-around gap-16">
          <!-- Static KanjiVG diagram -->
          <div class="flex flex-col items-center gap-1">
            <img
              v-if="strokeOrderUrl && !strokeError"
              :src="strokeOrderUrl"
              :alt="`Stroke order for ${kanji.literal}`"
              class="h-[160px] w-[160px] rounded border border-zinc-700 bg-white p-1"
              loading="lazy"
              @error="strokeError = true"
            >
            <span v-else-if="strokeError" class="h-[160px] w-[160px]" />
            <span class="text-xs text-zinc-600">Diagram</span>
          </div>

          <!-- Animated writer -->
          <div class="flex flex-col items-center gap-1">
            <ClientOnly>
              <KanjiStrokeAnimator :literal="kanji.literal" />
              <template #fallback>
                <div class="h-[160px] w-[160px] rounded border border-zinc-700 bg-zinc-800/60" />
              </template>
            </ClientOnly>
            <span class="text-xs text-zinc-600">Animated</span>
          </div>
        </div>
      </div>

      <!-- Step-by-step grid (full width, below the header row) -->
      <div class="mb-8">
        <span class="mb-2 block text-xs font-medium uppercase tracking-wide text-zinc-500">Stroke by stroke</span>
        <ClientOnly>
          <KanjiStrokeGrid :literal="kanji.literal" />
          <template #fallback>
            <p class="text-sm text-zinc-600">Loading…</p>
          </template>
        </ClientOnly>
      </div>

      <!-- Readings -->
      <div class="mb-8 grid gap-4 sm:grid-cols-3">
        <div v-if="kanji.on_readings.length" class="flex flex-col gap-1">
          <span class="text-xs font-medium uppercase tracking-wide text-zinc-500">On</span>
          <span class="font-japanese text-zinc-200">{{ kanji.on_readings.join('、') }}</span>
        </div>
        <div v-if="kanji.kun_readings.length" class="flex flex-col gap-1">
          <span class="text-xs font-medium uppercase tracking-wide text-zinc-500">Kun</span>
          <span class="font-japanese text-zinc-200">{{ kanji.kun_readings.join('、') }}</span>
        </div>
        <div v-if="kanji.nanori.length" class="flex flex-col gap-1">
          <span class="text-xs font-medium uppercase tracking-wide text-zinc-500">Nanori</span>
          <span class="font-japanese text-zinc-200">{{ kanji.nanori.join('、') }}</span>
        </div>
      </div>

      <!-- Meanings -->
      <div class="mb-10">
        <h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
          Meanings
        </h2>
        <div class="flex flex-col gap-2">
          <div
            v-for="group in meaningsByLang"
            :key="group.label"
            class="flex gap-3"
          >
            <span class="w-20 shrink-0 text-xs text-zinc-500">{{ group.label }}</span>
            <span class="text-zinc-200">{{ group.texts.join(' · ') }}</span>
          </div>
        </div>
      </div>

      <!-- Entries using this kanji -->
      <div v-if="entries.length">
        <h2 class="mb-4 text-xs font-medium uppercase tracking-wide text-zinc-500">
          Entries using this kanji
        </h2>
        <div class="flex flex-col gap-3">
          <EntryCard
            v-for="e in entries"
            :key="e.id"
            :entry="e"
            :lang="lang"
          />
        </div>
      </div>
    </template>
  </main>
</template>
