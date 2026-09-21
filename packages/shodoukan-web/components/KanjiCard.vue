<script setup lang="ts">
import type { Kanji } from '~/models/kanji'

const props = defineProps<{ kanji: Kanji; lang: string }>()

const meanings = computed(() =>
  props.kanji.meanings
    .filter((m) => m.lang === props.lang)
    .map((m) => m.text)
    .join(', '),
)

const jlptLabel = computed(() =>
  props.kanji.jlpt ? `N${props.kanji.jlpt}` : null,
)
</script>

<template>
  <div class="flex gap-6 rounded-lg border border-zinc-800 bg-zinc-800/50 px-6 py-5 transition hover:border-zinc-700">
    <div class="flex w-20 shrink-0 items-center justify-center font-japanese text-6xl font-bold text-zinc-100">
      {{ kanji.literal }}
    </div>

    <div class="flex min-w-0 flex-1 flex-col justify-center gap-2">
      <p class="text-base text-zinc-200">
        {{ meanings || '—' }}
      </p>

      <div class="flex flex-wrap items-center gap-3 text-sm text-zinc-400">
        <span v-if="kanji.on_readings.length">
          On: {{ kanji.on_readings.join('、') }}
        </span>
        <span v-if="kanji.kun_readings.length">
          Kun: {{ kanji.kun_readings.join('、') }}
        </span>
      </div>

      <div class="flex flex-wrap gap-2">
        <span
          v-if="jlptLabel"
          class="rounded bg-indigo-600/30 px-2 py-0.5 text-xs font-medium text-indigo-300"
        >
          JLPT {{ jlptLabel }}
        </span>
        <span
          v-if="kanji.grade"
          class="rounded bg-zinc-700 px-2 py-0.5 text-xs font-medium text-zinc-300"
        >
          Grade {{ kanji.grade }}
        </span>
        <span class="rounded bg-zinc-700 px-2 py-0.5 text-xs font-medium text-zinc-300">
          {{ kanji.stroke_count }} strokes
        </span>
      </div>
    </div>
  </div>
</template>
