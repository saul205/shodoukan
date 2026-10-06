<script setup lang="ts">
import { KanjiDrawingPad } from 'shodoukan-ui'
import type { DrawnPoint, ExerciseAnswer, HandwritingQuestion, StudyField } from '~/models/practice'
import { strokeProblem, VERDICT_COLORS, verdictOf } from '~/utils/verdict'

// Plays a handwriting card: draw the kanji the front asks for.
//
// Before answering, the front is a compact strip and the pad takes all the
// height left, as the largest square that fits, so it's comfortable on a
// phone. Below it: Deshacer (Backspace, Ctrl+Z), Borrar, Saltar (S, Escape)
// and Comprobar (Enter). Once answered, what matters is how the drawing went:
// the verdict and its score, the drawing next to the kanji (coloured stroke by
// stroke) and what was wrong with each stroke. The full card (the back) is
// one tap away on a phone, and beside them from `lg`. It measures the time to
// answer and emits; the session page talks to the API.
const props = defineProps<{ question: HandwritingQuestion; busy?: boolean; backFields?: StudyField[] }>()
const emit = defineEmits<{
  'answer': [answer: ExerciseAnswer, responseMs: number]
  'next': []
  'open-item': [itemId: number]
}>()

const shownAt = ref(0)
const strokes = ref<DrawnPoint[][]>([])
const cardOpen = ref(false)

watch(() => props.question.id, () => {
  shownAt.value = performance.now()
  const answer = props.question.answer
  strokes.value = answer?.type === 'strokes' ? answer.strokes : []
  cardOpen.value = false
}, { immediate: true })

const canSubmit = computed(() => !props.busy && !props.question.answered && strokes.value.length > 0)

function submit() {
  if (!canSubmit.value) return
  emit('answer', { type: 'strokes', strokes: strokes.value }, elapsed())
}

function skip() {
  if (props.busy || props.question.answered) return
  emit('answer', { type: 'skip' }, elapsed())
}

function undo() {
  if (!props.question.answered) strokes.value = strokes.value.slice(0, -1)
}

function clear() {
  if (!props.question.answered) strokes.value = []
}

function elapsed() {
  return Math.round(performance.now() - shownAt.value)
}

const verdict = computed(() => verdictOf(props.question))
const VERDICT_TEXT = { correct: '¡Correcto!', close: 'Mejorable', wrong: 'Fallada', skipped: 'Saltada' } as const
const TEXT_CLASSES = { success: 'text-success', warning: 'text-warning', error: 'text-error' } as const
const problems = computed(() =>
  (props.question.grade?.strokes ?? []).map(strokeProblem).filter((p): p is string => p !== null),
)

// The pad is the largest square that fits the room left for it.
const padBox = useTemplateRef<HTMLElement>('padBox')
const padSize = ref(0)
let observer: ResizeObserver | null = null
onMounted(() => {
  if (typeof ResizeObserver === 'undefined' || !padBox.value) return
  observer = new ResizeObserver(([entry]) => {
    if (entry) padSize.value = Math.floor(Math.min(entry.contentRect.width, entry.contentRect.height))
  })
  observer.observe(padBox.value)
})
onBeforeUnmount(() => observer?.disconnect())

// Where the shortcuts never apply: typing, a dialog, an open menu or list.
const OWN_KEYS = 'input, textarea, select, [contenteditable], [role="dialog"], [role="menu"], [role="listbox"], [role="combobox"]'

function onKey(event: KeyboardEvent) {
  if (event.defaultPrevented || event.repeat || event.altKey) return
  const target = event.target instanceof Element ? event.target : null
  if (target?.closest(OWN_KEYS)) return
  const command = event.ctrlKey || event.metaKey
  if (props.question.answered) {
    const free = !target || target === document.body
    if (!command && event.key === 'Enter' && free) {
      event.preventDefault()
      emit('next')
    }
    return
  }
  if (command) {
    if (event.key.toLowerCase() === 'z') {
      event.preventDefault()
      undo()
    }
    return
  }
  // A focused button keeps Enter and its own keys.
  if (target?.closest('button, a')) return
  if (event.key === 'Enter') {
    event.preventDefault()
    submit()
  }
  else if (event.key === 'Backspace') {
    event.preventDefault()
    undo()
  }
  else if (event.key === 'Escape' || event.key.toLowerCase() === 's') {
    skip()
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="flex min-h-0 flex-col gap-2 sm:gap-4">
    <template v-if="!question.answered">
      <StudyCard :question="question" compact class="shrink-0" />

      <div ref="padBox" class="flex min-h-48 flex-1 items-center justify-center" data-testid="pad-box">
        <KanjiDrawingPad
          v-model="strokes"
          :size="padSize ? `${padSize}px` : '100%'"
          :disabled="busy"
          class="max-h-full max-w-full"
        />
      </div>

      <div class="flex min-h-10 flex-wrap items-center gap-2" data-testid="bottom-row">
        <UButton
          icon="i-lucide-undo-2"
          color="neutral"
          variant="outline"
          size="lg"
          aria-label="Deshacer el último trazo"
          :disabled="busy || !strokes.length"
          data-testid="undo"
          @click="undo"
        />
        <UButton
          icon="i-lucide-eraser"
          color="neutral"
          variant="outline"
          size="lg"
          aria-label="Borrar el dibujo"
          :disabled="busy || !strokes.length"
          data-testid="clear"
          @click="clear"
        />
        <UButton
          label="Saltar"
          icon="i-lucide-skip-forward"
          color="neutral"
          variant="outline"
          size="lg"
          class="ml-auto"
          :disabled="busy"
          data-testid="skip"
          @click="skip"
        >
          <template #trailing>
            <UKbd value="S" class="hidden sm:inline-flex" />
          </template>
        </UButton>
        <UButton
          label="Comprobar"
          icon="i-lucide-check"
          size="lg"
          :disabled="!canSubmit"
          :loading="busy"
          data-testid="submit"
          @click="submit"
        >
          <template #trailing>
            <UKbd value="enter" class="hidden sm:inline-flex" />
          </template>
        </UButton>
      </div>
    </template>

    <template v-else>
      <div class="flex min-h-10 items-center justify-between gap-3" data-testid="bottom-row">
        <p class="font-medium sm:text-lg" :class="TEXT_CLASSES[VERDICT_COLORS[verdict]]" data-testid="verdict">
          {{ VERDICT_TEXT[verdict] }}
          <span v-if="question.grade" class="ml-1 text-sm text-dimmed tabular-nums" data-testid="score">· {{ question.grade.score }}</span>
        </p>
        <UButton label="Siguiente" size="lg" data-testid="next" @click="emit('next')">
          <template #trailing>
            <UKbd value="enter" class="hidden sm:inline-flex" />
          </template>
        </UButton>
      </div>

      <div class="grid min-h-0 flex-1 gap-4 overflow-y-auto lg:grid-cols-2">
        <div class="flex flex-col items-center gap-3">
          <StrokeComparison
            v-if="question.references?.length"
            :drawing="strokes"
            :references="question.references"
            :grade="question.grade"
          />
          <ul v-if="problems.length" class="space-y-0.5 text-sm text-toned" data-testid="stroke-problems">
            <li v-for="problem in problems" :key="problem">{{ problem }}</li>
          </ul>
        </div>

        <!-- The card: one tap away on phones, beside the drawing from lg. -->
        <UCollapsible v-model:open="cardOpen" class="lg:hidden" data-testid="card-toggle">
          <UButton
            :label="cardOpen ? 'Ocultar tarjeta' : 'Ver tarjeta'"
            icon="i-lucide-panel-bottom-open"
            color="neutral"
            variant="ghost"
            block
          />
          <template #content>
            <StudyCard :question="question" compact class="mt-2" @open-item="emit('open-item', $event)" />
          </template>
        </UCollapsible>
        <StudyCard :question="question" compact class="hidden lg:flex" @open-item="emit('open-item', $event)" />
      </div>
    </template>
  </div>
</template>
