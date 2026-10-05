<script setup lang="ts">
import type { ExerciseQuestion } from '~/models/practice'
import { formatResponseTime } from '~/utils/session-format'

// An answered question as it was played, for reviewing a session: its card
// with the back, the options with the right one and the pick marked, the
// verdict and how long it took. Compact, for a list.
const props = defineProps<{ question: ExerciseQuestion }>()
defineEmits<{ 'open-item': [itemId: number] }>()

const skipped = computed(() => props.question.answer?.type === 'skip')
const picked = computed(() => (props.question.answer?.type === 'option' ? props.question.answer.option : null))
const verdict = computed(() =>
  skipped.value
    ? { label: 'Saltada', color: 'warning' as const }
    : props.question.is_correct
      ? { label: 'Correcta', color: 'success' as const }
      : { label: 'Fallada', color: 'error' as const },
)
</script>

<template>
  <section class="space-y-3" data-testid="review-question">
    <div class="flex items-center gap-2">
      <span class="text-sm font-medium text-muted">#{{ question.position + 1 }}</span>
      <UBadge :label="verdict.label" :color="verdict.color" variant="subtle" data-testid="review-verdict" />
      <span v-if="question.response_ms !== null" class="ml-auto text-xs text-dimmed">
        {{ formatResponseTime(question.response_ms) }}
      </span>
    </div>
    <StudyCard :question="question" compact @open-item="$emit('open-item', $event)" />
    <ChoiceOptions
      :options="question.options"
      :picked="picked"
      :correct="question.correct_option"
      :japanese="question.answer_field !== 'meaning'"
      compact
      @open-item="$emit('open-item', $event)"
    />
  </section>
</template>
