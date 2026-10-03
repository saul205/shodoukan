<script setup lang="ts">
import { computed, type Component } from 'vue'
import type { Kanji } from '../models/kanji'

const props = withDefaults(
  defineProps<{ kanji: Kanji; lang: string; linkComponent?: Component | string }>(),
  { linkComponent: 'a' },
)

const meanings = computed(() =>
  props.kanji.meanings
    .filter((m) => m.lang === props.lang)
    .map((m) => m.text)
    .join(', '),
)

const linkProps = computed(() => {
  const href = `/kanji/${props.kanji.literal}`
  return props.linkComponent === 'a' ? { href } : { to: href }
})
</script>

<template>
  <component
    :is="linkComponent"
    v-bind="linkProps"
    class="flex min-w-56 flex-1 flex-col items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-800/50 px-3 py-4 text-center transition hover:border-zinc-600 hover:bg-zinc-800"
  >
    <span class="font-japanese text-4xl font-bold text-zinc-100">{{ kanji.literal }}</span>

    <span v-if="meanings.length" class="text-xs text-zinc-400">
      {{ meanings }}
    </span>
    <span v-if="kanji.kun_readings.length" class="text-xs text-zinc-400">
      Kun: {{ kanji.kun_readings.join('、') }}
    </span>
    <span v-if="kanji.on_readings.length" class="text-xs text-zinc-500">
      On: {{ kanji.on_readings.join('、') }}
    </span>

    <span
      v-if="kanji.jlpt"
      class="mt-1 rounded bg-indigo-600/30 px-1.5 py-0.5 text-xs font-medium text-indigo-300"
    >
      N{{ kanji.jlpt }}
    </span>
  </component>
</template>
