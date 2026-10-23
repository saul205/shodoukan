<script setup lang="ts">
import { computed } from 'vue'
import type { KanjiStroke } from '../models/kanji'
import { KANJIVG_SIZE, KANJIVG_STROKE_WIDTH, strokeStart } from '../utils/strokes'

const props = withDefaults(
  defineProps<{
    /** The strokes in writing order; `null` when the character has no drawing. */
    strokes: KanjiStroke[] | null
    loading?: boolean
    unavailableLabel?: string
    loadingLabel?: string
    /** Smallest width of a stroke frame (CSS length); frames grow up to twice it. */
    cellSize?: string
  }>(),
  {
    loading: false,
    unavailableLabel: 'Stroke order not available.',
    loadingLabel: 'Loading stroke order…',
    cellSize: '6rem',
  },
)

// The cell sizes go in inline styles: Tailwind 3 can't generate classes from a prop.

const PADDING = 6
const viewBox = `${-PADDING} ${-PADDING} ${KANJIVG_SIZE + 2 * PADDING} ${KANJIVG_SIZE + 2 * PADDING}`
const middle = KANJIVG_SIZE / 2

const starts = computed(() => props.strokes?.map(s => strokeStart(s.path)) ?? [])
</script>

<template>
  <p v-if="loading" class="text-sm text-zinc-600">
    {{ loadingLabel }}
  </p>

  <div
    v-else-if="strokes?.length"
    class="grid justify-center gap-1.5"
    :style="{ gridTemplateColumns: `repeat(auto-fit, minmax(${cellSize}, 1fr))` }"
  >
    <svg
      v-for="(stroke, i) in strokes"
      :key="i"
      :viewBox="viewBox"
      class="aspect-square w-full overflow-hidden rounded border border-zinc-700 bg-zinc-800/60"
      :style="{ maxWidth: `calc(${cellSize} * 2)` }"
    >
      <line :x1="middle" y1="0" :x2="middle" :y2="KANJIVG_SIZE" stroke="#3f3f46" stroke-width="0.4" stroke-dasharray="1.8 1.8" />
      <line x1="0" :y1="middle" :x2="KANJIVG_SIZE" :y2="middle" stroke="#3f3f46" stroke-width="0.4" stroke-dasharray="1.8 1.8" />

      <g fill="none" :stroke-width="KANJIVG_STROKE_WIDTH" stroke-linecap="round" stroke-linejoin="round">
        <path
          v-for="(previous, j) in strokes.slice(0, i)"
          :key="j"
          :d="previous.path"
          stroke="#52525b"
        />
        <path :d="stroke.path" stroke="#e4e4e7" />
      </g>
      <circle :cx="starts[i][0]" :cy="starts[i][1]" r="3.5" fill="#ef4444" />
    </svg>
  </div>

  <p v-else class="text-sm text-zinc-600">
    {{ unavailableLabel }}
  </p>
</template>
