<script setup lang="ts">
import type { ExerciseQuestion } from '~/models/practice'
import { formatResponseTime } from '~/utils/session-format'

// An answered question in a session review, collapsed to one line: its
// number, the verdict, the prompt, the right answer (and the wrong pick,
// struck through) and the time. Number, verdict and time have fixed widths,
// so every line's prompt starts at the same place. Opened (`v-model:open`), it shows the card
// and the options as they were played, in their compact form.
const props = defineProps<{ question: ExerciseQuestion }>()
defineEmits<{ 'open-item': [itemId: number] }>()
const open = defineModel<boolean>('open', { default: false })

const skipped = computed(() => props.question.answer?.type === 'skip')
const picked = computed(() => (props.question.answer?.type === 'option' ? props.question.answer.option : null))
const verdict = computed(() =>
  skipped.value
    ? { label: 'Saltada', color: 'warning' as const }
    : props.question.is_correct
      ? { label: 'Correcta', color: 'success' as const }
      : { label: 'Fallada', color: 'error' as const },
)

const japaneseAnswer = computed(() => props.question.answer_field !== 'meaning')
const prompt = computed(() => props.question.prompt.map(field => field.values.join('、')).join(' · '))
const rightText = computed(() =>
  props.question.correct_option !== null ? props.question.options[props.question.correct_option]?.text : undefined,
)
const wrongText = computed(() =>
  picked.value !== null && picked.value !== props.question.correct_option
    ? props.question.options[picked.value]?.text
    : undefined,
)
</script>

<template>
  <UCollapsible v-model:open="open" class="rounded-md border border-default" data-testid="review-question">
    <button
      type="button"
      class="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-elevated/50"
      :aria-expanded="open"
      data-testid="review-toggle"
    >
      <span class="w-10 shrink-0 text-right text-sm text-dimmed tabular-nums">#{{ question.position + 1 }}</span>
      <!-- Fixed width, so every summary starts at the same place. -->
      <UBadge
        :label="verdict.label"
        :color="verdict.color"
        variant="subtle"
        class="w-20 shrink-0 justify-center"
        data-testid="review-verdict"
      />
      <span class="min-w-0 flex-1 truncate" data-testid="review-summary">
        <span class="font-japanese">{{ prompt }}</span>
        <span class="mx-1.5 text-dimmed">→</span>
        <span :class="{ 'font-japanese': japaneseAnswer }" class="text-success">{{ rightText }}</span>
        <span v-if="wrongText" class="ml-2 text-error line-through" :class="{ 'font-japanese': japaneseAnswer }">{{ wrongText }}</span>
      </span>
      <span v-if="question.response_ms !== null" class="hidden w-14 shrink-0 text-right text-xs text-dimmed tabular-nums sm:inline">
        {{ formatResponseTime(question.response_ms) }}
      </span>
      <UIcon
        name="i-lucide-chevron-down"
        class="size-4 shrink-0 text-dimmed transition-transform"
        :class="{ 'rotate-180': open }"
      />
    </button>

    <template #content>
      <div class="space-y-3 border-t border-default p-3" data-testid="review-detail">
        <StudyCard :question="question" compact @open-item="$emit('open-item', $event)" />
        <ChoiceOptions
          :options="question.options"
          :picked="picked"
          :correct="question.correct_option"
          :japanese="japaneseAnswer"
          compact
          @open-item="$emit('open-item', $event)"
        />
      </div>
    </template>
  </UCollapsible>
</template>
