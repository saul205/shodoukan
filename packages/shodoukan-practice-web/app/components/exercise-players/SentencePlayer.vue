<script setup lang="ts">
import type { ExerciseAnswer, SentenceChoiceQuestion, StudyField } from '~/models/practice'
import { FIELD_LABELS } from '~/utils/study-fields'

// Plays a sentence question: a word in one of its sentences, the options
// below and the same bottom row as a choice card (`useOptionPlayer`: keys
// 1–N, S to skip, Enter for the next). Filling the gap shows a blank where
// the word goes, with the prompt fields (its meaning) as a hint; asking the
// word's reading or meaning underlines it. Once answered, the gap shows the
// word and the back of the card follows, compact. The translation shows when
// the exercise asks for it and the sentence has one.
const props = defineProps<{ question: SentenceChoiceQuestion; busy?: boolean; backFields?: StudyField[] }>()
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

const filling = computed(() => props.question.answer_field === 'writing')
const hints = computed(() => (props.question.answered ? [] : props.question.prompt.filter(f => f.field !== 'writing')))
const asked = computed(() => FIELD_LABELS[props.question.answer_field])
</script>

<template>
  <div class="flex min-h-0 flex-col gap-2 sm:gap-4">
    <UCard class="flex-[2_1_0%] sm:min-h-56 sm:flex-1" :ui="{ body: 'flex h-full flex-col justify-center gap-3 text-center' }" data-testid="sentence-card">
      <p class="text-xs font-medium uppercase tracking-wide text-dimmed">
        {{ filling ? 'Rellena el hueco' : `${asked} de la palabra` }}
      </p>
      <p class="font-japanese text-2xl leading-relaxed text-highlighted sm:text-3xl" data-testid="sentence">
        <span>{{ question.before }}</span>
        <span
          v-if="question.gap === null"
          class="mx-1 inline-block min-w-16 border-b-2 border-primary align-bottom"
          aria-label="hueco"
          data-testid="blank"
        >&nbsp;</span>
        <span
          v-else
          class="underline decoration-primary decoration-2 underline-offset-8"
          :class="{ 'text-primary': question.answered }"
          data-testid="gap"
        >{{ question.gap }}</span>
        <span>{{ question.after }}</span>
      </p>
      <p v-if="question.translation" class="text-muted" data-testid="translation">{{ question.translation }}</p>
      <p v-for="hint in hints" :key="hint.field" class="text-sm text-toned" data-testid="hint-field">
        <span class="text-dimmed">{{ FIELD_LABELS[hint.field] }}:</span> {{ hint.values.join('; ') }}
      </p>
      <StudyCard
        v-if="question.answered && question.back"
        :question="question"
        compact
        class="mx-auto w-full max-w-md text-left"
        @open-item="emit('open-item', $event)"
      />
    </UCard>
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
