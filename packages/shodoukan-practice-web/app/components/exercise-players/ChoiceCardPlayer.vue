<script setup lang="ts">
import type { ExerciseAnswer, ExerciseQuestion } from '~/models/practice'

// Plays a choice card: the card, its options (click or keys 1–N) and a
// bottom row that's always there (a hint, then the verdict and "Siguiente",
// or Enter). It fills the height it's given and the card takes what the
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
  picked.value = props.question.answer?.option ?? null
}, { immediate: true })

function pick(option: number) {
  if (props.busy || props.question.answered) return
  picked.value = option
  emit('answer', { type: 'option', option }, Math.round(performance.now() - shownAt.value))
}

function onKey(event: KeyboardEvent) {
  // Not while typing, or while a dialog (the item detail) is open.
  const typing = event.target instanceof Element
    && event.target.closest('input, textarea, [contenteditable], [role="dialog"]')
  if (event.repeat || typing) return
  if (props.question.answered) {
    if (event.key === 'Enter') {
      event.preventDefault()
      emit('next')
    }
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
          :class="question.is_correct ? 'text-success' : 'text-error'"
          data-testid="verdict"
        >
          {{ question.is_correct ? '¡Correcto!' : 'Fallada' }}
        </p>
        <UButton label="Siguiente" size="lg" data-testid="next" @click="emit('next')">
          <template #trailing>
            <UKbd value="enter" class="hidden sm:inline-flex" />
          </template>
        </UButton>
      </template>
      <p v-else class="hidden text-sm text-dimmed sm:block" data-testid="hint">
        Elige con un clic o con las teclas 1–{{ question.options.length }}
      </p>
    </div>
  </div>
</template>
