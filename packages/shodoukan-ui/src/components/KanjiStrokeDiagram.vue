<script setup lang="ts">
import { computed } from 'vue'
import type { KanjiStroke } from '../models/kanji'
import { KANJIVG_PADDING, KANJIVG_SIZE, KANJIVG_STROKE_WIDTH } from '../utils/strokes'

const props = withDefaults(
  defineProps<{
    /** The strokes in writing order; `null` (or empty) draws an empty frame. */
    strokes: KanjiStroke[] | null
    /** Width and height of the drawing: px, or any CSS length (`'100%'`). */
    size?: number | string
    /** A colour (any CSS colour) per stroke, by index; missing ones keep the default. */
    colors?: (string | undefined)[]
    /** Strokes drawn faintly underneath, e.g. a reference to compare with. */
    ghost?: KanjiStroke[] | null
    /** Whether to number the strokes that have a label. */
    numbers?: boolean
  }>(),
  { size: 160, numbers: true, colors: () => [], ghost: null },
)

const viewBox = `${-KANJIVG_PADDING} ${-KANJIVG_PADDING} ${KANJIVG_SIZE + 2 * KANJIVG_PADDING} ${KANJIVG_SIZE + 2 * KANJIVG_PADDING}`
const length = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))
</script>

<template>
  <svg
    :viewBox="viewBox"
    class="rounded border border-zinc-700 bg-zinc-800/60"
    :style="{ width: length, height: length }"
  >
    <g v-if="ghost?.length" fill="none" :stroke-width="KANJIVG_STROKE_WIDTH" stroke-linecap="round" stroke-linejoin="round" stroke="#52525b" data-ghost>
      <path v-for="(stroke, i) in ghost" :key="i" :d="stroke.path" />
    </g>
    <g fill="none" :stroke-width="KANJIVG_STROKE_WIDTH" stroke-linecap="round" stroke-linejoin="round" stroke="#e4e4e7">
      <path
        v-for="(stroke, i) in strokes ?? []"
        :key="i"
        :d="stroke.path"
        :style="colors[i] ? { stroke: colors[i] } : undefined"
      />
    </g>
    <g v-if="numbers" fill="#a1a1aa" font-size="8">
      <template v-for="(stroke, i) in strokes ?? []" :key="i">
        <text v-if="stroke.label" :x="stroke.label[0]" :y="stroke.label[1]">{{ i + 1 }}</text>
      </template>
    </g>
  </svg>
</template>
