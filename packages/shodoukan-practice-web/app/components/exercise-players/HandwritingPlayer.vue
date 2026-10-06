<script setup lang="ts">
import { KanjiDrawingPad } from 'shodoukan-ui'
import type { DrawnPoint, ExerciseAnswer, HandwritingQuestion, StudyField } from '~/models/practice'
import { strokeProblem, VERDICT_COLORS, verdictOf } from '~/utils/verdict'

// Plays a handwriting card: draw the kanji the front asks for.
//
// Before answering, the front is a compact strip and the pad takes all the
// height left, as the largest square that fits, so it's comfortable on a
// phone and never pushes the page into scrolling: the pad is measured on a box
// its own size can't change (it sits there absolutely positioned). Below it: Deshacer (Backspace, Ctrl+Z), Borrar, Saltar (S, Escape)
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

// The pad, and the comparison once answered, are the largest squares that fit
// the room left for them. Each box is measured, not its content, and the
// boxes come and go with the question, so the observer follows them.
const padBox = useTemplateRef<HTMLElement>('padBox')
const compareBox = useTemplateRef<HTMLElement>('compareBox')
const padRoom = ref({ width: 0, height: 0 })
const compareRoom = ref({ width: 0, height: 0 })

function observe(box: Ref<HTMLElement | null>, room: Ref<{ width: number; height: number }>) {
  if (typeof ResizeObserver === 'undefined') return
  const observer = new ResizeObserver(([entry]) => {
    if (entry) room.value = { width: entry.contentRect.width, height: entry.contentRect.height }
  })
  watch(box, (element, previous) => {
    if (previous) observer.unobserve(previous)
    if (element) observer.observe(element)
  }, { immediate: true, flush: 'post' })
  onBeforeUnmount(() => observer.disconnect())
}
observe(padBox, padRoom)
observe(compareBox, compareRoom)

const padSize = computed(() => Math.floor(Math.min(padRoom.value.width, padRoom.value.height)))
// The comparison: from sm two squares side by side over their captions (1.5rem);
// on a phone one square over the view buttons (2.5rem).
const COMPARE_GAP = 16
const CAPTION = 24
const PHONE_BUTTONS = 40
const compareSize = computed(() => {
  const { width, height } = compareRoom.value
  const side = Math.floor(Math.min((width - COMPARE_GAP) / 2, height - CAPTION))
  return side > 0 ? `${side}px` : undefined
})
const comparePhoneSize = computed(() => {
  const { width, height } = compareRoom.value
  const side = Math.floor(Math.min(width, height - PHONE_BUTTONS))
  return side > 0 ? `${side}px` : undefined
})

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
  <div class="flex min-h-0 flex-col gap-2 overflow-hidden sm:gap-4">
    <template v-if="!question.answered">
      <StudyCard :question="question" compact class="shrink-0" />

      <div ref="padBox" class="relative min-h-0 flex-1" data-testid="pad-box">
        <div class="absolute inset-0 flex items-center justify-center">
          <KanjiDrawingPad
            v-if="padSize > 0"
            v-model="strokes"
            :size="`${padSize}px`"
            :disabled="busy"
          />
        </div>
      </div>

      <div class="flex min-h-10 shrink-0 flex-wrap items-center gap-2" data-testid="bottom-row">
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
      <div class="flex min-h-10 shrink-0 items-center justify-between gap-3" data-testid="bottom-row">
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

      <!-- Phones: the comparison takes the room the card toggle leaves; from lg
           the card is a column beside it. Only the card's column may scroll. -->
      <div class="flex min-h-0 flex-1 flex-col gap-4 lg:grid lg:grid-cols-2">
        <div class="flex min-h-0 flex-1 flex-col gap-3">
          <div ref="compareBox" class="relative min-h-0 flex-1" data-testid="compare-box">
            <div class="absolute inset-0 flex items-center justify-center">
              <StrokeComparison
                v-if="question.references?.length"
                :drawing="strokes"
                :references="question.references"
                :grade="question.grade"
                :size="compareSize"
                :phone-size="comparePhoneSize"
              />
            </div>
          </div>
          <ul v-if="problems.length" class="shrink-0 space-y-0.5 text-center text-sm text-toned" data-testid="stroke-problems">
            <li v-for="problem in problems" :key="problem">{{ problem }}</li>
          </ul>
        </div>

        <div class="max-h-[50%] min-h-0 shrink-0 overflow-y-auto lg:max-h-none">
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
      </div>
    </template>
  </div>
</template>
