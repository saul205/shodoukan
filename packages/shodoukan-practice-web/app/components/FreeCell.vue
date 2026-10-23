<script setup lang="ts">
import { KanjiDrawingPad, KanjiStrokeDiagram, KANJIVG_STROKE_WIDTH, pointsToPath, type KanjiStroke, type StrokePoint } from 'shodoukan-ui'
import { MAX_STROKE_POINTS, MAX_STROKES } from '~/utils/drawing'

// One character written freely: drawn over its model in grey or, with the
// model hidden, from memory. Once `checked`, the drawing is laid over the
// model, strokes numbered, with the stroke counts under it; no grade. Its
// controls are the caller's; `touch` says a stroke started in it.
const props = defineProps<{ strokes: KanjiStroke[]; size: number; showModel: boolean; checked: boolean }>()
defineEmits<{ touch: [] }>()
const drawing = defineModel<StrokePoint[][]>({ default: () => [] })

const drawn = computed(() => drawing.value.map(points => ({ path: pointsToPath(points), label: points[0] ?? null })))
const counts = computed(() => `${drawing.value.length} / ${props.strokes.length} trazos`)
</script>

<template>
  <div class="relative">
    <KanjiStrokeDiagram v-if="checked" :strokes="drawn" :ghost="strokes" :size="`${size}px`" data-testid="free-result" />
    <div v-else @pointerdown.capture="$emit('touch')">
      <KanjiDrawingPad v-model="drawing" :size="`${size}px`" :max-strokes="MAX_STROKES" :max-points="MAX_STROKE_POINTS">
        <template #background>
          <g
            v-if="showModel"
            fill="none"
            :stroke-width="KANJIVG_STROKE_WIDTH"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke="#52525b"
            data-model
          >
            <path v-for="(stroke, i) in strokes" :key="i" :d="stroke.path" />
          </g>
        </template>
      </KanjiDrawingPad>
    </div>
    <span
      v-if="checked"
      class="absolute right-1.5 bottom-1 text-xs text-muted tabular-nums"
      data-testid="free-counts"
    >{{ counts }}</span>
  </div>
</template>
