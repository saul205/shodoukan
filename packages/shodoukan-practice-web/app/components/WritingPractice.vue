<script setup lang="ts">
import WordWritingBoard from '~/components/WordWritingBoard.vue'
import {
  PRACTICE_MODES,
  practiceSteps,
  wordChars,
  type PracticeItem,
  type PracticeMode,
} from '~/utils/writing-practice'

// Writing practice over a queue of items, kanji, kana or words: each one
// guided, free, or guided once then free a few times (`practiceSteps`). A
// strip on top says what (with its reading and meanings), how far along and
// how; the board below writes the whole item in one go. Once it's written:
// Otra vez (all of it again) or Siguiente (Enter). A lone character without a
// drawing in KanjiVG, or an item gone from the library, is passed over.
// Emits `finished` after the last item. Nothing is sent to the server.
const props = defineProps<{ items: PracticeItem[]; repetitions: number }>()
const emit = defineEmits<{ finished: [] }>()
const mode = defineModel<PracticeMode>('mode', { required: true })

const steps = computed(() => practiceSteps(props.items.length, mode.value, props.repetitions))
const position = ref(0)
/** Bumped to write the current item again from scratch. */
const attempt = ref(0)
const itemDone = ref(false)
const showModel = ref(true)

const step = computed(() => steps.value[Math.min(position.value, steps.value.length - 1)] ?? null)
const item = computed(() => (step.value ? props.items[step.value.index] ?? null : null))
const nextItem = computed(() => (step.value ? props.items[step.value.index + 1] ?? null : null))
const { text, status: itemStatus } = usePracticeItem(item, nextItem)

const chars = computed(() => wordChars(text.value?.text ?? ''))
const { strokes, status: strokesStatus } = useWordStrokes(chars)

const loading = computed(() => itemStatus.value === 'pending' || (chars.value.length > 0 && strokesStatus.value === 'pending'))
// Nothing to write: gone from the library, or a lone character KanjiVG doesn't draw.
const missing = computed(() => {
  if (loading.value) return null
  if (!text.value) return 'Ya no está en tu librería; se pasa al siguiente.'
  if (chars.value.length === 1 && !strokes.value?.[0]?.length) return 'KanjiVG no tiene este carácter; se pasa al siguiente.'
  return null
})
const finished = computed(() => itemDone.value || Boolean(missing.value))

// Another mode starts the current item over, in the new mode. The item is
// found in the steps of the mode it was played in: `steps` has already moved
// on to the new one.
watch(mode, (_, previous) => {
  const index = practiceSteps(props.items.length, previous, props.repetitions)[position.value]?.index ?? 0
  position.value = Math.max(0, steps.value.findIndex(s => s.index === index))
  again()
})

function again() {
  itemDone.value = false
  attempt.value++
}

function next() {
  // Nothing to write: every drawing of it is passed over.
  const target = missing.value ? lastStepOf(step.value?.index) + 1 : position.value + 1
  if (target >= steps.value.length) return emit('finished')
  position.value = target
  again()
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

const board = useTemplateRef<InstanceType<typeof WordWritingBoard>>('board')

// Where the shortcuts never apply: typing, an open menu or list.
const OWN_KEYS = 'input, textarea, select, [contenteditable], [role="menu"], [role="listbox"], [role="combobox"]'

function onKey(event: KeyboardEvent) {
  if (event.defaultPrevented || event.repeat || event.altKey) return
  const target = event.target instanceof Element ? event.target : null
  if (target?.closest(OWN_KEYS)) return
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
    event.preventDefault()
    board.value?.undo()
    return
  }
  if (event.key !== 'Enter' || event.ctrlKey || event.metaKey || target?.closest('button, a')) return
  event.preventDefault()
  if (finished.value) next()
  else board.value?.check()
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2 sm:gap-3" data-testid="writing-practice">
    <div class="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1">
      <div class="flex min-w-0 flex-1 basis-60 items-baseline gap-x-2">
        <span
          class="shrink-0 font-japanese leading-none text-highlighted"
          :class="chars.length > 1 ? 'text-2xl' : 'text-4xl'"
          data-testid="practice-text"
        >{{ text?.text }}</span>
        <span class="min-w-0 truncate text-sm text-muted">
          <span v-if="text?.reading" class="font-japanese" data-testid="practice-reading">{{ text.reading }}</span>
          <span v-if="text?.reading && text.meanings.length"> · </span>
          <span v-if="text?.meanings.length" data-testid="practice-meanings">{{ text.meanings.join(', ') }}</span>
        </span>
      </div>
      <div class="flex min-w-48 flex-1 items-center gap-3">
        <div class="min-w-0 flex-1 space-y-1">
          <div class="flex items-center justify-between gap-2 text-sm">
            <span class="text-toned" data-testid="practice-step">{{ stepLabel }}</span>
            <span class="text-dimmed tabular-nums" data-testid="practice-progress">{{ progress }} / {{ items.length }}</span>
          </div>
          <UProgress :model-value="progress" :max="items.length" size="xs" />
        </div>
        <USelect v-model="mode" :items="modeItems" class="w-36 shrink-0 sm:w-40" aria-label="Modo de práctica" data-testid="practice-mode" />
      </div>
    </div>

    <div v-if="loading" class="flex flex-1 items-center justify-center">
      <USkeleton class="aspect-square h-full max-h-80" />
    </div>

    <UEmpty
      v-else-if="missing"
      icon="i-lucide-image-off"
      :title="text ? `No hay orden de trazos para ${text.text}` : 'No se encuentra'"
      :description="missing"
      class="flex-1"
      data-testid="practice-missing"
    />

    <WordWritingBoard
      v-else-if="strokes && step"
      ref="board"
      :key="`${position}-${attempt}`"
      v-model:show-model="showModel"
      :chars="chars"
      :strokes="strokes"
      :guided="step.guided"
      @done="itemDone = true"
    />

    <div v-if="finished" class="flex min-h-10 shrink-0 items-center gap-2" data-testid="practice-next-row">
      <UButton
        v-if="!missing"
        label="Otra vez"
        icon="i-lucide-rotate-ccw"
        color="neutral"
        variant="outline"
        size="lg"
        data-testid="practice-again"
        @click="again"
      />
      <UButton label="Siguiente" size="lg" class="ml-auto" data-testid="practice-next" @click="next">
        <template #trailing>
          <UKbd value="enter" class="hidden sm:inline-flex" />
        </template>
      </UButton>
    </div>
  </div>
</template>
