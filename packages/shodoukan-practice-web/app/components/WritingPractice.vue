<script setup lang="ts">
import FreeWritingPad from '~/components/FreeWritingPad.vue'
import GuidedWritingPad from '~/components/GuidedWritingPad.vue'
import { PRACTICE_MODES, practiceSteps, type PracticeMode } from '~/utils/writing-practice'

// Writing practice over a queue of characters: each one guided, free, or
// guided once then free a few times (`practiceSteps`). A strip on top says
// which character, how far along and how; the pad takes the room left. Once
// a drawing is done: Otra vez (the same drawing again) or Siguiente (Enter).
// A character without a drawing in KanjiVG is shown and passed over. Emits
// `finished` after the last one. Nothing is sent to the server.
const props = defineProps<{ chars: string[]; repetitions: number }>()
const emit = defineEmits<{ finished: [] }>()
const mode = defineModel<PracticeMode>('mode', { required: true })

const steps = computed(() => practiceSteps(props.chars, mode.value, props.repetitions))
const position = ref(0)
/** Bumped to start the current drawing again from scratch. */
const attempt = ref(0)
const stepDone = ref(false)
const showModel = ref(true)

const step = computed(() => steps.value[Math.min(position.value, steps.value.length - 1)] ?? null)
const char = computed(() => step.value?.char ?? '')
const { strokes, status } = useKanjiStrokes(char)
const missing = computed(() => status.value !== 'pending' && !strokes.value?.length)

// Another mode starts the current character over, in the new mode.
watch(mode, () => {
  const index = step.value?.index ?? 0
  position.value = Math.max(0, steps.value.findIndex(s => s.index === index))
  reset()
})

function reset() {
  stepDone.value = false
  attempt.value++
}

function next() {
  if (position.value >= steps.value.length - 1) return emit('finished')
  // Every drawing of a character without one is passed over at once.
  const index = step.value?.index
  position.value = missing.value ? lastStepOf(index) + 1 : position.value + 1
  if (position.value >= steps.value.length) return emit('finished')
  reset()
}

function lastStepOf(index: number | undefined) {
  let last = position.value
  while (steps.value[last + 1]?.index === index) last++
  return last
}

const stepLabel = computed(() => {
  if (!step.value) return ''
  if (step.value.guided) return 'Guiado'
  const free = mode.value === 'guided-free' || props.repetitions > 1
  return free ? `Libre · ${step.value.repetition} de ${props.repetitions}` : 'Libre'
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
  if (stepDone.value || missing.value) next()
  else free.value?.check()
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="flex min-h-0 flex-1 flex-col gap-2 sm:gap-3" data-testid="writing-practice">
    <div class="flex shrink-0 items-center gap-3">
      <span class="font-japanese text-4xl leading-none text-highlighted" data-testid="practice-char">{{ char }}</span>
      <div class="min-w-0 flex-1 space-y-1">
        <div class="flex items-center justify-between gap-2 text-sm">
          <span class="text-toned" data-testid="practice-step">{{ stepLabel }}</span>
          <span class="text-dimmed tabular-nums" data-testid="practice-progress">{{ progress }} / {{ chars.length }}</span>
        </div>
        <UProgress :model-value="progress" :max="chars.length" size="xs" />
      </div>
      <USelect v-model="mode" :items="modeItems" class="w-40 shrink-0" aria-label="Modo de práctica" data-testid="practice-mode" />
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
        :key="`${position}-${attempt}`"
        :strokes="strokes"
        @done="stepDone = true"
      />
      <FreeWritingPad
        v-else
        ref="free"
        :key="`${position}-${attempt}`"
        v-model:show-model="showModel"
        :strokes="strokes"
        @done="stepDone = true"
      />
    </template>

    <div v-if="stepDone || missing" class="flex min-h-10 shrink-0 items-center gap-2" data-testid="practice-next-row">
      <UButton
        v-if="!missing"
        label="Otra vez"
        icon="i-lucide-rotate-ccw"
        color="neutral"
        variant="outline"
        size="lg"
        data-testid="practice-again"
        @click="reset"
      />
      <UButton label="Siguiente" size="lg" class="ml-auto" data-testid="practice-next" @click="next">
        <template #trailing>
          <UKbd value="enter" class="hidden sm:inline-flex" />
        </template>
      </UButton>
    </div>
  </div>
</template>
