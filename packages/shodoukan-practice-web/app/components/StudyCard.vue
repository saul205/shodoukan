<script setup lang="ts">
import type { ExerciseQuestion, ShownField, StudyField } from '~/models/practice'
import { FIELD_LABELS } from '~/utils/study-fields'

// The card of a question: one face at a time, so nothing is reserved for the
// other and the session fits a phone's screen. Before answering, the front
// (the prompt fields and what's asked); once answered, the card turns to the
// back, composed from the fields the backend sends: the prompt fields as the
// headline, the asked field below them, then the exercise's other back fields,
// smaller. It fills the height its parent gives it, but never less than the
// back is estimated to need (from the fields it'll have: the question's and the
// exercise's `backFields`), so turning it doesn't resize it; a longer back
// grows it. Japanese fields use the Japanese font, larger on larger screens.
// `compact` is the smaller card of a session review: only the back, sized by
// its content.
const props = defineProps<{ question: ExerciseQuestion; backFields?: StudyField[]; compact?: boolean }>()
defineEmits<{ 'open-item': [itemId: number] }>()

function japanese(field: ShownField) {
  return field.field !== 'meaning'
}

function joined(field: ShownField) {
  return field.values.join(japanese(field) ? '、' : '; ')
}

// The back split in its three parts. The backend sends the prompt fields and
// the answer first and never repeats a field; one the item has no value for
// is left out.
const back = computed(() => {
  const fields = props.question.back ?? []
  const prompt = props.question.prompt_fields
  return {
    headline: fields.filter(field => prompt.includes(field.field)),
    answer: fields.find(field => field.field === props.question.answer_field),
    extras: fields.filter(field => !prompt.includes(field.field) && field.field !== props.question.answer_field),
  }
})

const showBack = computed(() => props.question.answered && !!props.question.back)

// The back's height on a phone, in rem, from the line heights of the classes
// below: the card's padding (p-4), a headline row per prompt field (text-4xl),
// the answer's label and value (text-xs + text-2xl), the separator and a row
// per extra field (text-base, gap-y-1), "Ver detalle" (size sm) and the gaps
// (gap-3). The back only ever leaves out fields the item lacks, so this can
// over-reserve a little but not under, except for values that wrap.
const BACK_REM = { padding: 2, headline: 2.5, answer: 3, extra: 1.75, separator: 0.75, button: 2, gap: 0.75 }

const reservedRem = computed(() => {
  const { prompt_fields: prompt, answer_field: answer } = props.question
  const extras = (props.backFields ?? []).filter(field => !prompt.includes(field) && field !== answer).length
  const content = prompt.length * BACK_REM.headline + BACK_REM.gap + BACK_REM.answer
    + (extras ? BACK_REM.gap + BACK_REM.separator + extras * BACK_REM.extra : 0)
  return BACK_REM.padding + content + BACK_REM.gap + BACK_REM.button
})
</script>

<template>
  <UCard
    :ui="{ root: 'flex flex-col [perspective:1000px]', body: 'flex flex-1 flex-col' }"
    :style="compact ? undefined : { minHeight: `${reservedRem}rem` }"
    data-testid="study-card"
  >
    <Transition
      mode="out-in"
      enter-active-class="transition duration-200 ease-out motion-reduce:transition-none"
      enter-from-class="[transform:rotateY(90deg)] opacity-0"
      leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
      leave-to-class="[transform:rotateY(-90deg)] opacity-0"
    >
      <div
        v-if="showBack"
        :key="`back-${question.id}`"
        class="flex flex-1 flex-col"
        :class="compact ? 'gap-2' : 'gap-3 sm:gap-4'"
        data-testid="back"
      >
        <div class="flex flex-1 flex-col gap-3 sm:gap-4" :class="{ 'justify-center': !compact }">
          <div class="flex flex-wrap items-end justify-center gap-x-6 gap-y-1 text-center" data-testid="back-headline">
            <p
              v-for="field in back.headline"
              :key="field.field"
              class="text-highlighted"
              :class="japanese(field)
                ? ['font-japanese font-bold', compact ? 'text-2xl sm:text-3xl' : 'text-4xl sm:text-5xl lg:text-6xl']
                : ['font-medium', compact ? 'text-lg' : 'text-xl sm:text-2xl lg:text-3xl']"
              :title="FIELD_LABELS[field.field]"
            >
              {{ joined(field) }}
            </p>
          </div>

          <div v-if="back.answer" class="text-center" data-testid="back-answer">
            <p class="text-xs uppercase tracking-wide text-dimmed sm:text-sm">{{ FIELD_LABELS[back.answer.field] }}</p>
            <p
              class="font-medium text-success"
              :class="japanese(back.answer)
                ? ['font-japanese', compact ? 'text-xl' : 'text-2xl sm:text-3xl lg:text-4xl']
                : compact ? 'text-base' : 'text-lg sm:text-xl lg:text-2xl'"
            >
              {{ joined(back.answer) }}
            </p>
          </div>

          <template v-if="back.extras.length">
            <USeparator />
            <dl class="mx-auto grid grid-cols-[auto_1fr] items-baseline gap-x-4 gap-y-1" data-testid="back-extras">
              <template v-for="field in back.extras" :key="field.field">
                <dt class="text-xs uppercase tracking-wide text-dimmed">{{ FIELD_LABELS[field.field] }}</dt>
                <dd
                  class="text-default"
                  :class="japanese(field)
                    ? ['font-japanese', compact ? 'text-base' : 'text-base sm:text-lg']
                    : compact ? 'text-sm' : 'text-sm sm:text-base'"
                >
                  {{ joined(field) }}
                </dd>
              </template>
            </dl>
          </template>
        </div>

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
      </div>

      <div
        v-else
        :key="`front-${question.id}`"
        class="flex flex-1 flex-col items-center justify-center text-center"
        :class="compact ? 'gap-1' : 'gap-3 sm:gap-4'"
        data-testid="front"
      >
        <div v-for="field in question.prompt" :key="field.field" data-testid="prompt">
          <p class="text-xs uppercase tracking-wide text-dimmed sm:text-sm">{{ FIELD_LABELS[field.field] }}</p>
          <p
            class="text-highlighted"
            :class="japanese(field)
              ? ['font-japanese font-bold', compact ? 'text-3xl sm:text-4xl' : 'text-5xl sm:text-6xl lg:text-7xl']
              : ['font-medium', compact ? 'text-lg sm:text-xl' : 'text-2xl sm:text-3xl lg:text-4xl']"
          >
            {{ joined(field) }}
          </p>
        </div>
        <p class="text-sm text-muted sm:text-base">¿{{ FIELD_LABELS[question.answer_field] }}?</p>
      </div>
    </Transition>
  </UCard>
</template>
