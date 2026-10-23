<script setup lang="ts">
import { KanjiStrokeDiagram, pointsToPath } from 'shodoukan-ui'
import type { DrawnPoint, ReferenceWord, WordGrade } from '~/models/practice'
import { STROKE_STATUS_COLORS, strokeProblem, VERDICT_COLORS } from '~/utils/verdict'

// A word written a character per cell, next to the word it was graded
// against: each cell's drawing over its character (faint), coloured stroke by
// stroke, with the character and its score. Picking a cell compares it side
// by side (`StrokeComparison`) and lists what was wrong with its strokes;
// `compact` (the review) shows them smaller.
const props = withDefaults(defineProps<{
  cells: DrawnPoint[][][]
  words: ReferenceWord[]
  grade: WordGrade | null
  compact?: boolean
}>(), { compact: false })

const TEXT_CLASSES = { success: 'text-success', warning: 'text-warning', error: 'text-error' } as const

const selected = ref(0)
const word = computed(() => props.words.find(w => w.text === props.grade?.matched) ?? props.words[0] ?? null)

const results = computed(() =>
  (word.value?.characters ?? []).map((reference, i) => {
    const grade = props.grade?.cells[i] ?? null
    const colors: (string | undefined)[] = []
    for (const feedback of grade?.strokes ?? []) {
      if (feedback.drawn !== null) colors[feedback.drawn] = STROKE_STATUS_COLORS[feedback.status]
    }
    const drawing = props.cells[i] ?? []
    return { reference, grade, drawing, colors, strokes: drawing.map(points => ({ path: pointsToPath(points), label: null })) }
  }),
)
const current = computed(() => results.value[selected.value] ?? null)
const problems = computed(() => {
  const grade = current.value?.grade
  if (!grade) return []
  // Another character altogether says more than what's off with its strokes.
  const other = grade.looks_like ? [`Parece ${grade.looks_like}.`] : []
  return [...other, ...grade.strokes.map(strokeProblem).filter((p): p is string => p !== null)]
})
</script>

<template>
  <div class="flex flex-col items-center gap-3" data-testid="word-comparison">
    <div class="flex flex-wrap justify-center gap-2">
      <button
        v-for="(result, i) in results"
        :key="i"
        type="button"
        class="flex flex-col items-center gap-1 rounded p-1"
        :class="i === selected ? 'bg-elevated ring-1 ring-primary/60' : 'hover:bg-elevated/50'"
        :aria-pressed="i === selected"
        :aria-label="`Carácter ${i + 1}: ${result.reference.literal}`"
        data-testid="cell-result"
        @click="selected = i"
      >
        <KanjiStrokeDiagram
          :strokes="result.strokes"
          :colors="result.colors"
          :ghost="result.reference.strokes"
          :numbers="false"
          :size="compact ? '3rem' : '4.5rem'"
        />
        <span class="flex items-center gap-1 text-xs">
          <span class="font-japanese text-sm text-highlighted">{{ result.reference.literal }}</span>
          <span v-if="result.grade" class="tabular-nums" :class="TEXT_CLASSES[VERDICT_COLORS[result.grade.verdict]]">
            {{ result.grade.score }}
          </span>
        </span>
      </button>
    </div>

    <StrokeComparison
      v-if="current"
      :drawing="current.drawing"
      :references="[current.reference]"
      :grade="current.grade"
      :size="compact ? '8rem' : '10rem'"
      :compact="compact"
    />
    <ul v-if="problems.length" class="space-y-0.5 text-center text-sm text-toned" data-testid="stroke-problems">
      <li v-for="problem in problems" :key="problem">{{ problem }}</li>
    </ul>
  </div>
</template>
