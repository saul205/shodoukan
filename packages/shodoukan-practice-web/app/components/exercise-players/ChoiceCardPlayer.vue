<script setup lang="ts">
import type { ExerciseAnswer, ExerciseQuestion } from '~/models/practice'

// Plays a choice card: the card, its options (click or keys 1–N) and a
// bottom row that's always there ("Saltar", or S / Escape; then the verdict
// and "Siguiente", or Enter). A skip counts as a miss and shows the solution. It fills the height it's given and the card takes what the
// options and the row leave, so answering moves nothing. It measures the time
// to answer and emits; the session page talks to the API.
const props = defineProps<{ question: ExerciseQuestion; busy?: boolean }>()
const emit = defineEmits<{
  'answer': [answer: ExerciseAnswer, responseMs: number]
  'next': []
  'open-item': [itemId: number]
}>()

const shownAt = ref(0)
const picked = ref<number | null>(null)

watch(() => props.question.id, () => {
  shownAt.value = performance.now()
  const answer = props.question.answer
  picked.value = answer?.type === 'option' ? answer.option : null
}, { immediate: true })

function pick(option: number) {
  if (props.busy || props.question.answered) return
  picked.value = option
  emit('answer', { type: 'option', option }, elapsed())
}

function skip() {
  if (props.busy || props.question.answered) return
  emit('answer', { type: 'skip' }, elapsed())
}

function elapsed() {
  return Math.round(performance.now() - shownAt.value)
}

const skipped = computed(() => props.question.answer?.type === 'skip')

// Where the shortcuts never apply: typing, a dialog (the item detail), or an
// open menu or select list (the sidebar's), whose keys are their own.
const OWN_KEYS = 'input, textarea, select, [contenteditable], [role="dialog"], [role="menu"], [role="listbox"], [role="combobox"]'

function onKey(event: KeyboardEvent) {
  if (event.defaultPrevented || event.repeat || event.ctrlKey || event.metaKey || event.altKey) return
  const target = event.target instanceof Element ? event.target : null
  if (target?.closest(OWN_KEYS)) return
  if (props.question.answered) {
    // Enter on a focused control ("Terminar", a link, a detail button) is that
    // control's; it means "next" only from the page itself or an option.
    const free = !target || target === document.body || target.closest('[data-option-shortcuts]')
    if (event.key === 'Enter' && free) {
      event.preventDefault()
      emit('next')
    }
    return
  }
  if (event.key === 'Escape' || event.key.toLowerCase() === 's') {
    skip()
    return
  }
  const option = Number(event.key) - 1
  if (Number.isInteger(option) && option >= 0 && option < props.question.options.length) pick(option)
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="flex flex-col gap-3 sm:gap-4">
    <StudyCard :question="question" class="min-h-56 flex-1" @open-item="emit('open-item', $event)" />
    <ChoiceOptions
      :options="question.options"
      :picked="picked"
      :correct="question.correct_option"
      :japanese="question.answer_field !== 'meaning'"
      :disabled="busy"
      @pick="pick"
      @open-item="emit('open-item', $event)"
    />
    <div class="flex min-h-10 items-center justify-between gap-3" data-testid="bottom-row">
      <template v-if="question.answered">
        <p
          class="font-medium sm:text-lg"
          :class="skipped ? 'text-warning' : question.is_correct ? 'text-success' : 'text-error'"
          data-testid="verdict"
        >
          {{ skipped ? 'Saltada' : question.is_correct ? '¡Correcto!' : 'Fallada' }}
        </p>
        <UButton label="Siguiente" size="lg" data-testid="next" @click="emit('next')">
          <template #trailing>
            <UKbd value="enter" class="hidden sm:inline-flex" />
          </template>
        </UButton>
      </template>
      <template v-else>
        <p class="hidden text-sm text-dimmed sm:block" data-testid="hint">
          Elige con un clic o con las teclas 1–{{ question.options.length }}
        </p>
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
      </template>
    </div>
  </div>
</template>
