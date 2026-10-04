<script setup lang="ts">
import type { ExerciseQuestion, ShownField } from '~/models/practice'
import { FIELD_LABELS } from '~/utils/study-fields'

// The card of a question, in two halves that are always there, so answering
// never resizes it: the front (the prompt fields, and what's asked) and the
// back (a placeholder until answered; then the prompt, the answer and the
// exercise's back fields, scrolling inside if long). It fills the height its
// parent gives it; Japanese fields use the Japanese font, larger on larger
// screens.
defineProps<{ question: ExerciseQuestion }>()
defineEmits<{ 'open-item': [itemId: number] }>()

function japanese(field: ShownField) {
  return field.field !== 'meaning'
}

function joined(field: ShownField) {
  return field.values.join(japanese(field) ? '、' : '; ')
}
</script>

<template>
  <UCard
    :ui="{ root: 'flex flex-col', body: 'flex min-h-0 flex-1 flex-col gap-4 sm:gap-6' }"
    data-testid="study-card"
  >
    <div class="flex flex-1 flex-col items-center justify-center gap-3 text-center sm:gap-4">
      <div v-for="field in question.prompt" :key="field.field" data-testid="prompt">
        <p class="text-xs uppercase tracking-wide text-dimmed sm:text-sm">{{ FIELD_LABELS[field.field] }}</p>
        <p
          class="text-highlighted"
          :class="japanese(field)
            ? 'font-japanese text-5xl font-bold sm:text-6xl lg:text-7xl'
            : 'text-2xl font-medium sm:text-3xl lg:text-4xl'"
        >
          {{ joined(field) }}
        </p>
      </div>
      <p class="text-sm text-muted sm:text-base">¿{{ FIELD_LABELS[question.answer_field] }}?</p>
    </div>

    <USeparator />

    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto" data-testid="back-area">
      <template v-if="question.answered && question.back">
        <dl class="my-auto grid gap-x-6 gap-y-2 sm:grid-cols-[auto_1fr]" data-testid="back">
          <template v-for="field in question.back" :key="field.field">
            <dt class="text-xs uppercase tracking-wide text-dimmed sm:pt-1.5 sm:text-sm">{{ FIELD_LABELS[field.field] }}</dt>
            <dd
              class="text-default"
              :class="japanese(field) ? 'font-japanese text-lg sm:text-xl lg:text-2xl' : 'text-base sm:text-lg lg:text-xl'"
            >
              {{ joined(field) }}
            </dd>
          </template>
        </dl>
        <div v-if="question.item_id !== null" class="flex justify-end">
          <UButton
            label="Ver detalle"
            icon="i-lucide-info"
            color="neutral"
            variant="ghost"
            size="sm"
            data-testid="open-item"
            @click="$emit('open-item', question.item_id)"
          />
        </div>
      </template>
      <div
        v-else
        class="flex flex-1 flex-col items-center justify-center gap-2 text-dimmed"
        data-testid="back-placeholder"
      >
        <UIcon name="i-lucide-rotate-3d" class="size-8" />
        <p class="text-sm">Responde para ver el reverso</p>
      </div>
    </div>
  </UCard>
</template>
