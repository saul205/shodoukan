<script setup lang="ts">
import type { Entry } from '~/models/entry'

const props = defineProps<{ entry: Entry; lang: string }>()

const primaryForm = computed(() => props.entry.kanji_readings[0]?.kanji ?? props.entry.readings[0]?.text ?? '')

const reading = computed(() =>
  props.entry.kanji_readings.length ? props.entry.readings[0]?.text ?? '' : '',
)

const filteredSenses = computed(() =>
  props.entry.senses.filter((s) => s.glosses.some((g) => g.lang === props.lang)),
)

const jlptLabel = computed(() => (props.entry.jlpt ? `N${props.entry.jlpt}` : null))
</script>

<template>
  <div class="rounded-lg border border-zinc-800 bg-zinc-800/50 px-6 py-5">
    <div class="mb-3 flex items-baseline gap-3">
      <span class="font-japanese text-2xl font-bold text-zinc-100">{{ primaryForm }}</span>
      <span v-if="reading" class="font-japanese text-base text-zinc-400">{{ reading }}</span>
      <span
        v-if="jlptLabel"
        class="ml-auto rounded bg-indigo-600/30 px-2 py-0.5 text-xs font-medium text-indigo-300"
      >
        JLPT {{ jlptLabel }}
      </span>
    </div>

    <ol class="flex flex-col gap-1.5">
      <li
        v-for="(sense, i) in filteredSenses"
        :key="sense.id"
        class="flex gap-2 text-sm"
      >
        <span class="shrink-0 text-zinc-500">{{ i + 1 }}.</span>
        <div class="flex flex-col gap-0.5">
          <div class="flex flex-wrap gap-1">
            <span
              v-for="pos in sense.pos"
              :key="pos"
              class="rounded bg-zinc-700 px-1.5 py-0.5 text-xs text-zinc-400"
            >
              {{ pos }}
            </span>
          </div>
          <span class="text-zinc-200">
            {{ sense.glosses.filter((g) => g.lang === lang).map((g) => g.text).join('; ') }}
          </span>
        </div>
      </li>
    </ol>
  </div>
</template>
