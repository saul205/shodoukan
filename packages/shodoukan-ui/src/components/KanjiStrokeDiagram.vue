<script setup lang="ts">
import type { KanjiStroke } from '../models/kanji'
import { KANJIVG_SIZE, KANJIVG_STROKE_WIDTH } from '../utils/strokes'

withDefaults(
  defineProps<{
    /** The strokes in writing order; `null` (or empty) draws an empty frame. */
    strokes: KanjiStroke[] | null
    /** Width and height of the drawing, in px. */
    size?: number
  }>(),
  { size: 160 },
)

const PADDING = 6
const viewBox = `${-PADDING} ${-PADDING} ${KANJIVG_SIZE + 2 * PADDING} ${KANJIVG_SIZE + 2 * PADDING}`
</script>

<template>
  <svg
    :viewBox="viewBox"
    class="rounded border border-zinc-700 bg-zinc-800/60"
    :style="{ width: `${size}px`, height: `${size}px` }"
  >
    <g fill="none" :stroke-width="KANJIVG_STROKE_WIDTH" stroke-linecap="round" stroke-linejoin="round" stroke="#e4e4e7">
      <path v-for="(stroke, i) in strokes ?? []" :key="i" :d="stroke.path" />
    </g>
    <g fill="#a1a1aa" font-size="8">
      <template v-for="(stroke, i) in strokes ?? []" :key="i">
        <text v-if="stroke.label" :x="stroke.label[0]" :y="stroke.label[1]">{{ i + 1 }}</text>
      </template>
    </g>
  </svg>
</template>
