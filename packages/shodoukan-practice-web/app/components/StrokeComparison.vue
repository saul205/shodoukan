<script setup lang="ts">
import { KanjiStrokeDiagram, pointsToPath, type KanjiStroke } from 'shodoukan-ui'
import type { DrawnPoint, HandwritingGrade, ReferenceKanji } from '~/models/practice'
import { STROKE_STATUS_COLORS } from '~/utils/verdict'

// A drawing next to the kanji it was graded against (KanjiVG, numbered), each
// drawn stroke coloured by its grade: green right, amber backwards, out of
// order or imprecise, red extra; a reference stroke that wasn't drawn is red.
// Both share KanjiVG's space, so they also overlay as they are. From `sm` they
// sit side by side; on a phone there's room for one square, so it shows the
// drawing over the faint reference, or the two in turn.
const props = withDefaults(defineProps<{
  drawing: DrawnPoint[][]
  references: ReferenceKanji[]
  grade: HandwritingGrade | null
  /** Width of each square on `sm` and up (CSS length). */
  size?: string
  /** Width of the one square on a phone (CSS length); fills its width up to a cap by default. */
  phoneSize?: string
  compact?: boolean
}>(), { size: '12rem', phoneSize: undefined, compact: false })

const reference = computed(() =>
  props.references.find(r => r.literal === props.grade?.matched) ?? props.references[0] ?? null,
)
const referenceStrokes = computed<KanjiStroke[]>(() => reference.value?.strokes ?? [])
const drawnStrokes = computed<KanjiStroke[]>(() => props.drawing.map(points => ({ path: pointsToPath(points), label: null })))

const drawnColors = computed(() => {
  const colors: (string | undefined)[] = []
  for (const feedback of props.grade?.strokes ?? []) {
    if (feedback.drawn !== null) colors[feedback.drawn] = STROKE_STATUS_COLORS[feedback.status]
  }
  return colors
})
const referenceColors = computed(() => {
  const colors: (string | undefined)[] = []
  for (const feedback of props.grade?.strokes ?? []) {
    if (feedback.status === 'missing' && feedback.reference !== null) colors[feedback.reference] = STROKE_STATUS_COLORS.missing
  }
  return colors
})

const mode = ref<'overlay' | 'drawing' | 'reference'>('overlay')
const modes = [
  { value: 'overlay', label: 'Superpuesto' },
  { value: 'drawing', label: 'Tu dibujo' },
  { value: 'reference', label: 'Kanji' },
] as const
</script>

<template>
  <div class="flex flex-col items-center gap-2" data-testid="stroke-comparison">
    <!-- Phones: one square, the views in turn. -->
    <div class="flex w-full flex-col items-center gap-2 sm:hidden">
      <div
        class="aspect-square"
        :class="phoneSize ? '' : ['w-full', compact ? 'max-w-40' : 'max-w-72']"
        :style="phoneSize ? { width: phoneSize } : undefined"
      >
        <KanjiStrokeDiagram
          v-if="mode === 'reference'"
          :strokes="referenceStrokes"
          :colors="referenceColors"
          size="100%"
        />
        <KanjiStrokeDiagram
          v-else
          :strokes="drawnStrokes"
          :colors="drawnColors"
          :ghost="mode === 'overlay' ? referenceStrokes : null"
          :numbers="false"
          size="100%"
          data-testid="comparison-drawing"
        />
      </div>
      <div v-if="!compact" class="flex gap-1" role="group" aria-label="Qué ver">
        <UButton
          v-for="item in modes"
          :key="item.value"
          :label="item.label"
          size="xs"
          :color="mode === item.value ? 'primary' : 'neutral'"
          :variant="mode === item.value ? 'subtle' : 'ghost'"
          :aria-pressed="mode === item.value"
          @click="mode = item.value"
        />
      </div>
    </div>

    <!-- From sm: side by side. -->
    <div class="hidden items-start gap-4 sm:flex">
      <figure class="flex flex-col items-center gap-1">
        <KanjiStrokeDiagram :strokes="drawnStrokes" :colors="drawnColors" :numbers="false" :size="size" />
        <figcaption class="text-xs text-dimmed">Tu dibujo</figcaption>
      </figure>
      <figure class="flex flex-col items-center gap-1">
        <KanjiStrokeDiagram :strokes="referenceStrokes" :colors="referenceColors" :size="size" data-testid="comparison-reference" />
        <figcaption class="font-japanese text-xs text-dimmed">{{ reference?.literal }}</figcaption>
      </figure>
    </div>
  </div>
</template>
