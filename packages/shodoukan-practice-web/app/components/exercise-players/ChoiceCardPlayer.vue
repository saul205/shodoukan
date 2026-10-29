<script setup lang="ts">
import type { ChoiceQuestion, ExerciseAnswer, StudyField } from '~/models/practice'

// Plays a choice card: the card, its options (click or keys 1–N) and a
// bottom row that's always there ("Saltar", or S / Escape; then the verdict
// and "Siguiente", or Enter). A skip counts as a miss and shows the solution.
// It fills the height it's given: on phones the card and the options share it
// 2:3 (neither below its content), so the options grow into room the card
// doesn't need; from `sm` the card takes what the options and the row leave.
// Either way answering moves nothing and a phone never scrolls. It measures
// the time to answer and emits (`useOptionPlayer`, shared with the sentence
// player); the session page talks to the API.
const props = defineProps<{ question: ChoiceQuestion; busy?: boolean; backFields?: StudyField[] }>()
const emit = defineEmits<{
  'answer': [answer: ExerciseAnswer, responseMs: number]
  'next': []
  'open-item': [itemId: number]
}>()

const { picked, pick, skip, skipped } = useOptionPlayer(
  () => props.question,
  () => props.busy,
  (answer, responseMs) => emit('answer', answer, responseMs),
  () => emit('next'),
)
</script>

<template>
  <div class="flex min-h-0 flex-col gap-2 sm:gap-4">
    <StudyCard :question="question" :back-fields="backFields" class="flex-[2_1_0%] sm:min-h-56 sm:flex-1" @open-item="emit('open-item', $event)" />
    <ChoiceOptions
      class="flex-[3_1_0%] sm:flex-none"
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
