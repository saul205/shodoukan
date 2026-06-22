<script setup lang="ts">
import type { Entry, ScoreBreakdown, Sense } from '~/models/entry'
import { glossLang } from '~/models/kanji'
import { shortenPos } from '~/utils/pos'

const props = defineProps<{ entry: Entry; lang: string }>()

const langCode = computed(() => glossLang(props.lang))

const primaryForm = computed(() =>
  props.entry.kanji_readings[0]?.kanji ?? props.entry.readings[0]?.text ?? '',
)

const reading = computed(() =>
  props.entry.kanji_readings.length ? (props.entry.readings[0]?.text ?? '') : '',
)

const isCommon = computed(() => props.entry.is_common)

const filteredSenses = computed(() =>
  props.entry.senses.filter(s => s.glosses.some(g => g.lang === langCode.value)),
)

const jlptLabel = computed(() => (props.entry.jlpt ? `N${props.entry.jlpt}` : null))
const hasTags = computed(() => !!(jlptLabel.value || isCommon.value))

const debugFields = computed(() => {
  const s = props.entry.score
  if (!s) return null

  const sortValue = s.composite ?? (
    s.freq !== null && s.jlpt_bonus !== null ? s.freq + s.jlpt_bonus : null
  )

  const fields: { key: string; value: string; highlight?: boolean }[] = []
  if (sortValue !== null)
    fields.push({ key: 'sort', value: String(sortValue), highlight: true })

  const add = (key: keyof ScoreBreakdown, label: string) => {
    if (s[key] !== null && s[key] !== undefined)
      fields.push({ key: label, value: String(s[key]) })
  }
  add('freq', 'freq')
  add('jlpt_bonus', 'jlpt_bonus')
  add('exact_match', 'exact_match')
  add('fts_rank', 'fts_rank')
  add('sense_pos', 'sense_pos')
  add('total_senses', 'total_senses')
  add('composite', 'composite')
  return fields.length ? fields : null
})

function glossesFor(sense: Sense): string {
  return sense.glosses
    .filter(g => g.lang === langCode.value)
    .map(g => g.text)
    .join(' · ')
}

function notesFor(sense: Sense): string[] {
  return [...sense.misc, ...sense.info]
}
</script>

<template>
  <div class="rounded-lg border border-zinc-800 bg-zinc-800/50 px-6 py-5">
    <!-- Word identity: always full-width at the top -->
    <div class="mb-3">
      <div
        v-if="reading"
        class="mb-0.5 font-japanese text-sm leading-none text-zinc-400"
      >{{ reading }}</div>
      <div class="font-japanese text-2xl font-bold leading-tight text-zinc-100">
        {{ primaryForm }}
      </div>
    </div>

    <div class="flex flex-wrap items-start gap-x-4 gap-y-3">
      <div
        v-if="hasTags"
        class="flex flex-1 flex-wrap gap-1"
      >
        <span
          v-if="jlptLabel"
          class="min-w-max rounded bg-indigo-600/30 px-2 py-0.5 text-xs font-medium text-indigo-300"
        >JLPT {{ jlptLabel }}</span>
        <span
          v-if="isCommon"
          class="min-w-max rounded bg-teal-600/30 px-2 py-0.5 text-xs font-medium text-teal-300"
        >common</span>
      </div>

      <ol class="flex flex-col gap-2.5 [flex:100] min-w-fit">
        <li
          v-for="(sense, i) in filteredSenses"
          :key="sense.id"
          class="flex flex-col gap-0.5 text-sm"
        >
          <div class="flex flex-wrap items-center gap-1">
            <span class="shrink-0 text-zinc-500">{{ i + 1 }}.</span>
            <span
              v-for="pos in sense.pos"
              :key="pos"
              class="min-w-max rounded bg-zinc-700 px-1.5 py-0.5 text-xs text-zinc-400"
            >{{ shortenPos(pos) }}</span>
          </div>
          <p class="text-zinc-200">{{ glossesFor(sense) }}</p>
          <p
            v-if="notesFor(sense).length"
            class="text-xs italic text-zinc-500"
          >{{ notesFor(sense).join(' · ') }}</p>
        </li>
      </ol>
    </div>

    <div
      v-if="debugFields"
      class="mt-3 border-t border-zinc-700 pt-2 font-mono text-xs text-zinc-500"
    >
      <span
        v-for="field in debugFields"
        :key="field.key"
        class="mr-3"
        :class="field.highlight ? 'font-semibold text-amber-400' : ''"
      >{{ field.key }}: {{ field.value }}</span>
    </div>
  </div>
</template>
