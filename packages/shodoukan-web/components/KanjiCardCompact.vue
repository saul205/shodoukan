<script setup lang="ts">
import type { Kanji } from '~/models/kanji'

defineProps<{ kanji: Kanji }>()
</script>

<template>
  <div class="flex flex-col items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-800/50 px-3 py-4 text-center">
    <span class="font-japanese text-4xl font-bold text-zinc-100">{{ kanji.literal }}</span>

    <span v-if="kanji.kun_readings.length" class="text-xs text-zinc-400">
      {{ kanji.kun_readings.join('、') }}
    </span>
    <span v-if="kanji.on_readings.length" class="text-xs text-zinc-500">
      {{ kanji.on_readings.join('、') }}
    </span>

    <span
      v-if="kanji.jlpt"
      class="mt-1 rounded bg-indigo-600/30 px-1.5 py-0.5 text-xs font-medium text-indigo-300"
    >
      N{{ kanji.jlpt }}
    </span>
  </div>
</template>
