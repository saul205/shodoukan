<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import {
  KANJIVG_PADDING,
  KANJIVG_SIZE,
  KANJIVG_STROKE_WIDTH,
  pointsToPath,
  simplifyStroke,
  type StrokePoint,
} from '../utils/strokes'

// A square to draw a kanji in, with a finger, a pen or the mouse. It draws in
// KanjiVG's space (the 109 square plus the margin KanjiStrokeDiagram shows),
// so a drawing and a reference overlay without any conversion. Each stroke is
// simplified when the pointer lifts and appended to the model. Only the
// primary pointer draws, so a second finger or a palm doesn't scribble, and
// `touch-action: none` keeps the page from scrolling under the finger.
const props = withDefaults(
  defineProps<{
    /** Width and height: px, or any CSS length. */
    size?: number | string
    disabled?: boolean
    /** How far (in KanjiVG units) a point may stray from a straight line and still be dropped. */
    epsilon?: number
  }>(),
  { size: '100%', disabled: false, epsilon: 0.5 },
)
const strokes = defineModel<StrokePoint[][]>({ default: () => [] })
const emit = defineEmits<{ 'stroke-end': [stroke: StrokePoint[]] }>()

const MIN = -KANJIVG_PADDING
const SIDE = KANJIVG_SIZE + 2 * KANJIVG_PADDING
const viewBox = `${MIN} ${MIN} ${SIDE} ${SIDE}`
const CENTRE = KANJIVG_SIZE / 2
const length = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))

const svg = useTemplateRef<SVGSVGElement>('svg')
const current = ref<StrokePoint[] | null>(null)
let pointerId: number | null = null

function toPoint(event: PointerEvent): StrokePoint {
  const box = svg.value!.getBoundingClientRect()
  const clamp = (value: number) => Math.min(Math.max(value, MIN), MIN + SIDE)
  return [
    clamp(MIN + ((event.clientX - box.left) / (box.width || 1)) * SIDE),
    clamp(MIN + ((event.clientY - box.top) / (box.height || 1)) * SIDE),
  ]
}

function start(event: PointerEvent) {
  if (props.disabled || !event.isPrimary || event.button > 0 || pointerId !== null) return
  event.preventDefault()
  pointerId = event.pointerId
  svg.value?.setPointerCapture?.(event.pointerId)
  current.value = [toPoint(event)]
}

function move(event: PointerEvent) {
  if (event.pointerId !== pointerId || !current.value) return
  const events = event.getCoalescedEvents?.() ?? []
  for (const e of events.length ? events : [event]) {
    const point = toPoint(e)
    const last = current.value[current.value.length - 1]!
    if (Math.hypot(point[0] - last[0], point[1] - last[1]) >= 0.3) current.value.push(point)
  }
}

function end(event: PointerEvent) {
  if (event.pointerId !== pointerId || !current.value) return
  const stroke = simplifyStroke(current.value, props.epsilon)
  pointerId = null
  current.value = null
  strokes.value = [...strokes.value, stroke]
  emit('stroke-end', stroke)
}

/** Removes the last stroke. */
function undo() {
  strokes.value = strokes.value.slice(0, -1)
}

/** Removes every stroke. */
function clear() {
  strokes.value = []
}

defineExpose({ undo, clear })
</script>

<template>
  <svg
    ref="svg"
    :viewBox="viewBox"
    class="touch-none select-none rounded border border-zinc-700 bg-zinc-800/60"
    :class="disabled ? 'cursor-not-allowed opacity-60' : 'cursor-crosshair'"
    :style="{ width: length, height: length }"
    role="img"
    aria-label="Panel para dibujar el kanji"
    data-testid="drawing-pad"
    @pointerdown="start"
    @pointermove="move"
    @pointerup="end"
    @pointercancel="end"
  >
    <g stroke="#3f3f46" stroke-width="0.5" stroke-dasharray="2 2" data-guide>
      <line :x1="CENTRE" :y1="MIN" :x2="CENTRE" :y2="MIN + SIDE" />
      <line :x1="MIN" :y1="CENTRE" :x2="MIN + SIDE" :y2="CENTRE" />
    </g>
    <g fill="none" :stroke-width="KANJIVG_STROKE_WIDTH" stroke-linecap="round" stroke-linejoin="round" stroke="#e4e4e7">
      <path v-for="(stroke, i) in strokes" :key="i" :d="pointsToPath(stroke)" data-stroke />
      <path v-if="current" :d="pointsToPath(current)" data-current />
    </g>
  </svg>
</template>
