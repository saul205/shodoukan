<script setup lang="ts">
import type { ExerciseQuestion, ShownField } from '~/models/practice'
import { FIELD_LABELS } from '~/utils/study-fields'

// The card of a question: the front (the prompt fields, and what's asked)
// and, once answered, the back (the prompt, the answer and the exercise's
// back fields). Japanese fields use the Japanese font.
defineProps<{ question: ExerciseQuestion }>()
defineEmits<{ 'open-item': [itemId: number] }>()

function japanese(field: ShownField) {
  return field.field !== 'meaning'
}
</script>

<template>
  <UCard :ui="{ body: 'space-y-6' }" data-testid="study-card">
    <div class="space-y-4 text-center">
      <div v-for="field in question.prompt" :key="field.field" data-testid="prompt">
        <p class="text-xs uppercase tracking-wide text-dimmed">{{ FIELD_LABELS[field.field] }}</p>
        <p
          class="text-highlighted"
          :class="japanese(field) ? 'font-japanese text-5xl font-bold' : 'text-2xl font-medium'"
        >
          {{ field.values.join(japanese(field) ? '、' : '; ') }}
        </p>
      </div>
      <p class="text-sm text-muted">¿{{ FIELD_LABELS[question.answer_field] }}?</p>
    </div>

    <template v-if="question.answered && question.back">
      <USeparator />
      <dl class="grid gap-x-4 gap-y-2 sm:grid-cols-[auto_1fr]" data-testid="back">
        <template v-for="field in question.back" :key="field.field">
          <dt class="text-xs uppercase tracking-wide text-dimmed sm:pt-1">{{ FIELD_LABELS[field.field] }}</dt>
          <dd :class="japanese(field) ? 'font-japanese text-lg' : ''" class="text-default">
            {{ field.values.join(japanese(field) ? '、' : '; ') }}
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
  </UCard>
</template>
