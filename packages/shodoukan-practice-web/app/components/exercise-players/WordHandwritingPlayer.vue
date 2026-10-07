<script setup lang="ts">
import FreeCell from '~/components/FreeCell.vue'
import PracticeModal from '~/components/PracticeModal.vue'
import type { DrawnPoint, ExerciseAnswer, StudyField, WordHandwritingQuestion } from '~/models/practice'
import { fitCells } from '~/utils/writing-practice'
import { VERDICT_COLORS, verdictOf } from '~/utils/verdict'

// Plays a word handwriting card: write the word the front asks for (its
// spelling or its reading), a character per cell. The cells are laid out as
// the largest grid the room allows (`fitCells`: a row on a PC, two columns on
// a phone), or one at a time with a row to move between them when they'd be
// too small. Any cell can be drawn in; undo and clear act on the last one
// touched. Comprobar (Enter) sends every cell at once. Once answered: the
// verdict and score, and `WordComparison`: each character's drawing over its
// model, coloured by its grade, the selected one compared side by side.
const props = defineProps<{ question: WordHandwritingQuestion; busy?: boolean; backFields?: StudyField[] }>()
const emit = defineEmits<{
  'answer': [answer: ExerciseAnswer, responseMs: number]
  'next': []
  'open-item': [itemId: number]
}>()

const GAP = 12
/** Height of the row of small cells when one cell is drawn at a time. */
const ROW = 48

const shownAt = ref(0)
const cells = ref<DrawnPoint[][][]>([])
const current = ref(0)
const cardOpen = ref(false)

watch(() => props.question.id, () => {
  shownAt.value = performance.now()
  const answer = props.question.answer
  cells.value = answer?.type === 'cells'
    ? answer.cells
    : Array.from({ length: props.question.cell_count }, () => [])
  current.value = 0
  cardOpen.value = false
}, { immediate: true })

const anyDrawn = computed(() => cells.value.some(cell => cell.length))
const canSubmit = computed(() => !props.busy && !props.question.answered && anyDrawn.value)

function elapsed() {
  return Math.round(performance.now() - shownAt.value)
}

function submit() {
  if (canSubmit.value) emit('answer', { type: 'cells', cells: cells.value }, elapsed())
}

function skip() {
  if (!props.busy && !props.question.answered) emit('answer', { type: 'skip' }, elapsed())
}

// Not while the word is being sent: the server grades what was sent.
function undo() {
  if (!props.busy && !props.question.answered) cells.value[current.value] = cells.value[current.value]!.slice(0, -1)
}

function clear() {
  if (!props.busy && !props.question.answered) cells.value[current.value] = []
}

function move(step: number) {
  current.value = Math.min(Math.max(current.value + step, 0), cells.value.length - 1)
}

const box = useTemplateRef<HTMLElement>('box')
const room = useMeasuredBox(box)
const grid = computed(() => fitCells(props.question.cell_count, room.value.width, room.value.height, GAP))
const size = computed(() => grid.value?.size ?? Math.floor(Math.min(room.value.width, room.value.height - ROW - GAP)))
const shown = computed(() => (grid.value ? cells.value.map((_, i) => i) : [current.value]))

// Once answered.
const verdict = computed(() => verdictOf(props.question))
const VERDICT_TEXT = { correct: '¡Correcto!', close: 'Mejorable', wrong: 'Fallada', skipped: 'Saltada' } as const
const TEXT_CLASSES = { success: 'text-success', warning: 'text-warning', error: 'text-error' } as const
const word = computed(() =>
  props.question.words?.find(w => w.text === props.question.grade?.matched) ?? props.question.words?.[0] ?? null,
)


// Practising the word opens over the session, which stays as it is.
const overlay = useOverlay()

function practise() {
  const itemId = props.question.item_id
  if (itemId === null) return
  overlay.create(PracticeModal, { destroyOnClose: true }).open({
    items: [{ kind: 'entry', id: itemId }],
    title: `Practicar ${word.value?.text ?? ''}`,
  })
}

// Where the shortcuts never apply: typing, a dialog, an open menu or list.
const OWN_KEYS = 'input, textarea, select, [contenteditable], [role="dialog"], [role="menu"], [role="listbox"], [role="combobox"]'

function onKey(event: KeyboardEvent) {
  if (event.defaultPrevented || event.repeat || event.altKey) return
  const target = event.target instanceof Element ? event.target : null
  if (target?.closest(OWN_KEYS)) return
  const command = event.ctrlKey || event.metaKey
  if (props.question.answered) {
    if (!command && event.key === 'Enter' && (!target || target === document.body)) {
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
  <div class="flex min-h-0 flex-col gap-2 overflow-hidden sm:gap-3">
    <template v-if="!question.answered">
      <StudyCard :question="question" compact class="shrink-0" />

      <div ref="box" class="relative min-h-0 flex-1" data-testid="cells-box">
        <div v-if="size > 0" class="absolute inset-0 flex flex-col items-center justify-center" :style="{ gap: `${GAP}px` }">
          <div v-if="!grid && cells.length > 1" class="flex max-w-full shrink-0 items-center gap-1.5 overflow-x-auto" data-testid="cell-row">
            <UButton icon="i-lucide-chevron-left" color="neutral" variant="ghost" aria-label="Casilla anterior" @click="move(-1)" />
            <button
              v-for="(cell, i) in cells"
              :key="i"
              type="button"
              class="flex size-10 shrink-0 items-center justify-center rounded border text-sm tabular-nums"
              :class="i === current ? 'border-primary bg-primary/10 text-highlighted' : cell.length ? 'border-default text-highlighted' : 'border-default text-dimmed'"
              :aria-current="i === current ? 'step' : undefined"
              :aria-label="`Casilla ${i + 1}`"
              data-testid="cell-button"
              @click="current = i"
            >
              {{ i + 1 }}
            </button>
            <UButton icon="i-lucide-chevron-right" color="neutral" variant="ghost" aria-label="Casilla siguiente" @click="move(1)" />
          </div>
          <div
            class="grid justify-center"
            :style="{ gap: `${GAP}px`, gridTemplateColumns: `repeat(${grid?.columns ?? 1}, ${size}px)` }"
            :data-columns="grid?.columns ?? 0"
            data-testid="cells-grid"
          >
            <div
              v-for="i in shown"
              :key="i"
              class="rounded"
              :class="{ 'ring-2 ring-primary/60': grid && cells.length > 1 && i === current }"
            >
              <FreeCell
                v-model="cells[i]"
                :strokes="[]"
                :size="size"
                :show-model="false"
                :checked="false"
                @touch="current = i"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="flex min-h-10 shrink-0 flex-wrap items-center gap-2" data-testid="bottom-row">
        <UButton
          icon="i-lucide-undo-2"
          color="neutral"
          variant="outline"
          size="lg"
          aria-label="Deshacer el último trazo"
          :disabled="busy || !cells[current]?.length"
          data-testid="undo"
          @click="undo"
        />
        <UButton
          icon="i-lucide-eraser"
          color="neutral"
          variant="outline"
          size="lg"
          aria-label="Borrar la casilla"
          :disabled="busy || !cells[current]?.length"
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
        <UButton
          v-if="question.item_id !== null"
          label="Practicar palabra"
          icon="i-lucide-pen-line"
          color="neutral"
          variant="outline"
          size="lg"
          class="ml-auto"
          data-testid="practise"
          @click="practise"
        />
        <UButton label="Siguiente" size="lg" data-testid="next" @click="emit('next')">
          <template #trailing>
            <UKbd value="enter" class="hidden sm:inline-flex" />
          </template>
        </UButton>
      </div>

      <div class="min-h-0 flex-1 space-y-4 overflow-y-auto">
        <WordComparison :cells="cells" :words="question.words ?? []" :grade="question.grade" />

        <UCollapsible v-model:open="cardOpen" data-testid="card-toggle">
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
      </div>
    </template>
  </div>
</template>
