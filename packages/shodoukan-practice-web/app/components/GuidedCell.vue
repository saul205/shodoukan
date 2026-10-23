<script setup lang="ts">
import { KanjiDrawingPad, KANJIVG_SIZE, KANJIVG_STROKE_WIDTH, matchStroke, strokeStart, type KanjiStroke, type StrokePoint } from 'shodoukan-ui'
import { MAX_STROKE_POINTS } from '~/utils/drawing'
import type { GuidedProgress } from '~/utils/writing-practice'

// One character written guided: the character in grey, the strokes done so
// far in ink, and the next one animated over and over from a red dot where it
// starts. A stroke traced over it that follows it (`matchStroke`) becomes the
// model's own stroke; one that doesn't is wiped, with a hint. Its controls
// are the caller's: it reports how it goes (`progress`), emits `done` once
// every stroke is in, and exposes undo, restart and skip.
const props = defineProps<{ strokes: KanjiStroke[]; size: number }>()
const emit = defineEmits<{ progress: [progress: GuidedProgress]; done: [] }>()

const done = ref(0)
const misses = ref(0)
const hint = ref<string | null>(null)
// What the pad holds while a stroke is being traced: emptied as it's judged.
const drawing = ref<StrokePoint[][]>([])

const current = computed(() => props.strokes[done.value] ?? null)
const finished = computed(() => done.value >= props.strokes.length)
const start = computed(() => (current.value ? strokeStart(current.value.path) : null))

watch([done, misses, hint], () => {
  emit('progress', { done: done.value, total: props.strokes.length, hint: hint.value, misses: misses.value })
}, { immediate: true })

function onStroke(stroke: StrokePoint[]) {
  drawing.value = []
  if (!current.value) return
  const match = matchStroke(stroke, current.value.path)
  if (match.ok) return skip()
  misses.value++
  hint.value = hintFor(stroke, match.reversed)
}

function hintFor(stroke: StrokePoint[], reversed: boolean): string {
  if (reversed) return 'Al revés: empieza en el punto rojo.'
  const [x, y] = stroke[0]!
  const [sx, sy] = start.value!
  // Further than a tenth of the square from where it starts.
  if (Math.hypot(x - sx, y - sy) > KANJIVG_SIZE / 10) return 'Empieza en el punto rojo.'
  return 'Sigue la forma del trazo resaltado.'
}

/** Takes the next stroke as done: matched, or skipped after a few misses. */
function skip() {
  if (finished.value) return
  done.value++
  misses.value = 0
  hint.value = null
  if (finished.value) emit('done')
}

function undo() {
  if (!done.value || finished.value) return
  done.value--
  misses.value = 0
  hint.value = null
}

function restart() {
  done.value = 0
  misses.value = 0
  hint.value = null
}

defineExpose({ undo, restart, skip })
</script>

<template>
  <KanjiDrawingPad
    v-model="drawing"
    :size="`${size}px`"
    :disabled="finished"
    :max-strokes="1"
    :max-points="MAX_STROKE_POINTS"
    @stroke-end="onStroke"
  >
    <template #background>
      <g fill="none" :stroke-width="KANJIVG_STROKE_WIDTH" stroke-linecap="round" stroke-linejoin="round">
        <path v-for="(stroke, i) in strokes" :key="`model-${i}`" :d="stroke.path" stroke="#52525b" data-model />
        <path v-for="(stroke, i) in strokes.slice(0, done)" :key="`done-${i}`" :d="stroke.path" stroke="#e4e4e7" data-done />
        <path
          v-if="current"
          :key="`current-${done}`"
          :d="current.path"
          pathLength="1"
          stroke="#818cf8"
          class="guided-stroke"
          data-current
        />
      </g>
      <circle v-if="start" :cx="start[0]" :cy="start[1]" r="2.5" fill="#ef4444" data-start />
    </template>
  </KanjiDrawingPad>
</template>

<style scoped>
/* The next stroke draws itself from its start, holds, and starts again.
   pathLength="1" makes it one unit long, so a dash of 1 hides it whole. */
.guided-stroke {
  stroke-dasharray: 1;
  animation: guided-stroke 1.6s ease-in-out infinite;
}

@keyframes guided-stroke {
  0% {
    stroke-dashoffset: 1;
  }
  60%,
  100% {
    stroke-dashoffset: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .guided-stroke {
    animation: none;
  }
}
</style>
