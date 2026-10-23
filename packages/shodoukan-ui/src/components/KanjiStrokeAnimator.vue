<script setup lang="ts">
import { ref } from 'vue'
import type { KanjiStroke } from '../models/kanji'
import { KANJIVG_SIZE, KANJIVG_STROKE_WIDTH } from '../utils/strokes'

const props = withDefaults(
  defineProps<{
    /** The strokes in writing order; `null` (or empty) disables the animation. */
    strokes: KanjiStroke[] | null
    playLabel?: string
    playingLabel?: string
    /** Width and height of the drawing, in px. */
    size?: number
  }>(),
  { playLabel: 'Play', playingLabel: 'Playing…', size: 160 },
)

/** How long each stroke takes to draw, and the pause before the next one (ms). */
const STROKE_MS = 500
const PAUSE_MS = 250

const PADDING = 6
const viewBox = `${-PADDING} ${-PADDING} ${KANJIVG_SIZE + 2 * PADDING} ${KANJIVG_SIZE + 2 * PADDING}`

/** Times played: the drawn strokes are re-rendered (`:key`) to restart the animation. */
const runs = ref(0)
const animating = ref(false)

function play() {
  if (animating.value || !props.strokes?.length) return
  runs.value++
  // With reduced motion the strokes are drawn at once, with no animation to wait for.
  animating.value = !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

function strokeStyle(i: number) {
  return { animationDuration: `${STROKE_MS}ms`, animationDelay: `${i * (STROKE_MS + PAUSE_MS)}ms` }
}

function onStrokeDrawn(i: number) {
  if (i === props.strokes!.length - 1) animating.value = false
}
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <svg
      :viewBox="viewBox"
      class="rounded border border-zinc-700 bg-zinc-800/60"
      :style="{ width: `${size}px`, height: `${size}px` }"
    >
      <g fill="none" :stroke-width="KANJIVG_STROKE_WIDTH" stroke-linecap="round" stroke-linejoin="round">
        <path v-for="(stroke, i) in strokes ?? []" :key="i" :d="stroke.path" stroke="#3f3f46" />
        <g v-if="runs" :key="runs" stroke="#e4e4e7">
          <path
            v-for="(stroke, i) in strokes ?? []"
            :key="i"
            :d="stroke.path"
            pathLength="1"
            :class="{ 'kanji-stroke-draw': animating }"
            :style="animating ? strokeStyle(i) : undefined"
            @animationend="onStrokeDrawn(i)"
          />
        </g>
      </g>
    </svg>
    <button
      :disabled="!strokes?.length || animating"
      class="rounded bg-indigo-600/30 px-3 py-1 text-xs font-medium text-indigo-300 transition hover:bg-indigo-600/50 disabled:opacity-40"
      @click="play"
    >
      {{ animating ? playingLabel : playLabel }}
    </button>
  </div>
</template>

<style scoped>
/* pathLength="1" makes every stroke one unit long, so a dash of 1 hides it
   whole and sliding the offset to 0 draws it from its start. */
.kanji-stroke-draw {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation-name: kanji-stroke-draw;
  animation-timing-function: ease-in-out;
  animation-fill-mode: forwards;
}

@keyframes kanji-stroke-draw {
  to {
    stroke-dashoffset: 0;
  }
}
</style>
