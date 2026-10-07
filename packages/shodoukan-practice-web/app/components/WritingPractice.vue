<script setup lang="ts">
import FreeWritingPad from '~/components/FreeWritingPad.vue'
import GuidedWritingPad from '~/components/GuidedWritingPad.vue'
import { PRACTICE_MODES, practiceSteps, wordChars, type PracticeItem, type PracticeMode } from '~/utils/writing-practice'

// Writing practice over a queue of items, kanji, kana or words: each one
// guided, free, or guided once then free a few times (`practiceSteps`). A
// word is written one character after another, with a row of cells showing
// which ones are done (a done one can be drawn again). A strip on top says
// what, how far along and how; the pad takes the room left. Once an item is
// written: Otra vez (all of it again) or Siguiente (Enter). A character
// without a drawing in KanjiVG is shown and passed over. Emits `finished`
// after the last item. Nothing is sent to the server.
const props = defineProps<{ items: PracticeItem[]; repetitions: number }>()
const emit = defineEmits<{ finished: [] }>()
const mode = defineModel<PracticeMode>('mode', { required: true })

const steps = computed(() => practiceSteps(props.items.map(item => item.text), mode.value, props.repetitions))
const position = ref(0)
/** The character of the item being written. */
const cell = ref(0)
/** Bumped to start the current drawing again from scratch. */
const attempt = ref(0)
const cellDone = ref(false)
const showModel = ref(true)

const step = computed(() => steps.value[Math.min(position.value, steps.value.length - 1)] ?? null)
const item = computed(() => (step.value ? props.items[step.value.index] ?? null : null))
const chars = computed(() => wordChars(step.value?.text ?? ''))
const isWord = computed(() => chars.value.length > 1)
const char = computed(() => chars.value[cell.value] ?? '')
const lastCell = computed(() => cell.value >= chars.value.length - 1)

const { strokes, status } = useKanjiStrokes(char)
const missing = computed(() => status.value !== 'pending' && !strokes.value?.length)
const cellFinished = computed(() => cellDone.value || missing.value)

// Another mode starts the current item over, in the new mode.
watch(mode, () => {
  const index = step.value?.index ?? 0
  position.value = Math.max(0, steps.value.findIndex(s => s.index === index))
  restartItem()
})

function restartItem() {
  cell.value = 0
  redraw()
}

function redraw() {
  cellDone.value = false
  attempt.value++
}

function goToCell(index: number) {
  if (index > cell.value && !cellFinished.value) return
  cell.value = index
  redraw()
}

function nextCell() {
  if (!lastCell.value) goToCell(cell.value + 1)
}

function next() {
  // A lone character without a drawing: every drawing of it is passed over.
  const skipItem = missing.value && !isWord.value
  const target = skipItem ? lastStepOf(step.value?.index) + 1 : position.value + 1
  if (target >= steps.value.length) return emit('finished')
  position.value = target
  restartItem()
}

function lastStepOf(index: number | undefined) {
  let last = position.value
  while (steps.value[last + 1]?.index === index) last++
  return last
}

const stepLabel = computed(() => {
  if (!step.value) return ''
  if (step.value.guided) return 'Guiado'
  const counted = mode.value === 'guided-free' || props.repetitions > 1
  return counted ? `Libre · ${step.value.repetition} de ${props.repetitions}` : 'Libre'
})
const progress = computed(() => (step.value ? step.value.index + 1 : 0))
const modeItems = PRACTICE_MODES.map(({ value, label }) => ({ value, label }))

const guided = useTemplateRef<InstanceType<typeof GuidedWritingPad>>('guided')
const free = useTemplateRef<InstanceType<typeof FreeWritingPad>>('free')

// Where the shortcuts never apply: typing, an open menu or list.
const OWN_KEYS = 'input, textarea, select, [contenteditable], [role="menu"], [role="listbox"], [role="combobox"]'

function onKey(event: KeyboardEvent) {
  if (event.defaultPrevented || event.repeat || event.altKey) return
  const target = event.target instanceof Element ? event.target : null
  if (target?.closest(OWN_KEYS)) return
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
    event.preventDefault()
    ;(guided.value ?? free.value)?.undo()
    return
  }
  if (event.key !== 'Enter' || event.ctrlKey || event.metaKey || target?.closest('button, a')) return
  event.preventDefault()
  if (!cellFinished.value) free.value?.check()
  else if (lastCell.value) next()
  else nextCell()
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2 sm:gap-3" data-testid="writing-practice">
    <div class="flex shrink-0 items-center gap-3">
      <div class="min-w-0 shrink">
        <p class="truncate font-japanese leading-none text-highlighted" :class="isWord ? 'text-2xl' : 'text-4xl'" data-testid="practice-text">
          {{ step?.text }}
        </p>
        <p v-if="item?.reading" class="mt-1 truncate font-japanese text-sm text-muted" data-testid="practice-reading">{{ item.reading }}</p>
      </div>
      <div class="min-w-0 flex-1 space-y-1">
        <div class="flex items-center justify-between gap-2 text-sm">
          <span class="text-toned" data-testid="practice-step">{{ stepLabel }}</span>
          <span class="text-dimmed tabular-nums" data-testid="practice-progress">{{ progress }} / {{ items.length }}</span>
        </div>
        <UProgress :model-value="progress" :max="items.length" size="xs" />
      </div>
      <USelect v-model="mode" :items="modeItems" class="w-36 shrink-0 sm:w-40" aria-label="Modo de práctica" data-testid="practice-mode" />
    </div>

    <div v-if="isWord" class="flex shrink-0 gap-1.5 overflow-x-auto pb-1" role="list" aria-label="Caracteres" data-testid="practice-cells">
      <button
        v-for="(c, i) in chars"
        :key="i"
        type="button"
        role="listitem"
        class="flex size-10 shrink-0 items-center justify-center rounded border font-japanese text-xl transition"
        :class="i === cell
          ? 'border-primary bg-primary/10 text-highlighted'
          : i < cell ? 'border-default text-highlighted' : 'border-default text-dimmed'"
        :disabled="i > cell && !(i === cell + 1 && cellFinished)"
        :aria-current="i === cell ? 'step' : undefined"
        :aria-label="`Carácter ${i + 1}: ${c}`"
        data-testid="practice-cell"
        @click="goToCell(i)"
      >
        {{ c }}
      </button>
    </div>

    <div v-if="status === 'pending' && !strokes" class="flex flex-1 items-center justify-center">
      <USkeleton class="aspect-square h-full max-h-80" />
    </div>

    <UEmpty
      v-else-if="missing"
      icon="i-lucide-image-off"
      :title="`No hay orden de trazos para ${char}`"
      description="KanjiVG no tiene este carácter; se pasa al siguiente."
      class="flex-1"
      data-testid="practice-missing"
    />

    <template v-else-if="strokes && step">
      <GuidedWritingPad
        v-if="step.guided"
        ref="guided"
        :key="`${position}-${cell}-${attempt}`"
        :strokes="strokes"
        @done="cellDone = true"
      />
      <FreeWritingPad
        v-else
        ref="free"
        :key="`${position}-${cell}-${attempt}`"
        v-model:show-model="showModel"
        :strokes="strokes"
        @done="cellDone = true"
      />
    </template>

    <div v-if="cellFinished" class="flex min-h-10 shrink-0 items-center gap-2" data-testid="practice-next-row">
      <UButton
        v-if="!(missing && !isWord)"
        label="Otra vez"
        icon="i-lucide-rotate-ccw"
        color="neutral"
        variant="outline"
        size="lg"
        data-testid="practice-again"
        @click="isWord && !lastCell ? redraw() : restartItem()"
      />
      <UButton
        v-if="!lastCell"
        label="Siguiente carácter"
        size="lg"
        class="ml-auto"
        data-testid="practice-next-cell"
        @click="nextCell"
      >
        <template #trailing>
          <UKbd value="enter" class="hidden sm:inline-flex" />
        </template>
      </UButton>
      <UButton v-else label="Siguiente" size="lg" class="ml-auto" data-testid="practice-next" @click="next">
        <template #trailing>
          <UKbd value="enter" class="hidden sm:inline-flex" />
        </template>
      </UButton>
    </div>
  </div>
</template>
