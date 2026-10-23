<script setup lang="ts">
import { KanjiStrokeDiagram, pointsToPath } from 'shodoukan-ui'
import PracticeModal from '~/components/PracticeModal.vue'
import type { PracticeItem } from '~/utils/writing-practice'
import type { ExerciseQuestion } from '~/models/practice'
import { formatResponseTime } from '~/utils/session-format'
import { VERDICT_COLORS, VERDICT_LABELS, verdictOf } from '~/utils/verdict'

// An answered question in a session review, collapsed to one line: its
// number, the verdict, the prompt, the right answer (and a choice card's wrong
// pick, struck through; a drawing's thumbnail, a word's per character) and
// the time. Number, verdict
// and time have fixed widths, so every line's prompt starts at the same place.
// Opened (`v-model:open`), it shows the card and how it was answered, as it
// was played, in compact form: the options, the drawing next to the kanji, or
// the word cell by cell. A drawn kanji or word can be practised from there.
const props = defineProps<{ question: ExerciseQuestion }>()
defineEmits<{ 'open-item': [itemId: number] }>()
const open = defineModel<boolean>('open', { default: false })

const verdict = computed(() => {
  const kind = verdictOf(props.question)
  return { label: VERDICT_LABELS[kind], color: VERDICT_COLORS[kind] }
})

const choice = computed(() => (props.question.type === 'card.choice' ? props.question : null))
const handwriting = computed(() => (props.question.type === 'card.handwriting' ? props.question : null))
const written = computed(() => (props.question.type === 'card.handwriting_word' ? props.question : null))

const picked = computed(() => (props.question.answer?.type === 'option' ? props.question.answer.option : null))
const drawing = computed(() => (props.question.answer?.type === 'strokes' ? props.question.answer.strokes : []))
const cells = computed(() => (props.question.answer?.type === 'cells' ? props.question.answer.cells : []))
const thumbnails = computed(() => {
  const drawings = cells.value.length ? cells.value : drawing.value.length ? [drawing.value] : []
  return drawings.map(strokes => strokes.map(points => ({ path: pointsToPath(points), label: null })))
})

// A handwriting question's kanji can be practised right there, over the review.
const overlay = useOverlay()
const asked = computed(() => handwriting.value?.references?.[0]?.literal ?? written.value?.words?.[0]?.text ?? null)

function practise() {
  if (!asked.value) return
  const itemId = props.question.item_id
  // The item is the library kanji or word: practising it shows its own
  // meanings. A word gone from the library can't be practised.
  let items: PracticeItem[]
  if (written.value) {
    if (!itemId) return
    items = [{ kind: 'entry', id: itemId }]
  }
  else {
    items = itemId ? [{ kind: 'kanji', id: itemId }] : [{ kind: 'char', text: asked.value }]
  }
  overlay.create(PracticeModal, { destroyOnClose: true }).open({ items, title: `Practicar ${asked.value}` })
}

const japaneseAnswer = computed(() => props.question.answer_field !== 'meaning')
const prompt = computed(() => props.question.prompt.map(field => field.values.join('、')).join(' · '))
const rightText = computed(() => {
  if (handwriting.value) return handwriting.value.references?.map(r => r.literal).join('、')
  if (written.value) return written.value.words?.map(w => w.text).join('、')
  const q = choice.value
  return q && q.correct_option !== null ? q.options[q.correct_option]?.text : undefined
})
const wrongText = computed(() => {
  const q = choice.value
  return q && picked.value !== null && picked.value !== q.correct_option ? q.options[picked.value]?.text : undefined
})
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
      <span v-if="thumbnails.length" class="flex shrink-0 gap-0.5" data-testid="review-thumbnail">
        <KanjiStrokeDiagram
          v-for="(strokes, i) in thumbnails.slice(0, 4)"
          :key="i"
          :strokes="strokes"
          :numbers="false"
          :size="28"
        />
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
          v-if="choice"
          :options="choice.options"
          :picked="picked"
          :correct="choice.correct_option"
          :japanese="japaneseAnswer"
          compact
          @open-item="$emit('open-item', $event)"
        />
        <StrokeComparison
          v-else-if="handwriting?.references?.length && drawing.length"
          :drawing="drawing"
          :references="handwriting.references"
          :grade="handwriting.grade"
          size="8rem"
          compact
        />
        <WordComparison
          v-else-if="written?.words?.length && cells.length"
          :cells="cells"
          :words="written.words"
          :grade="written.grade"
          compact
        />
        <div v-if="asked && (!written || question.item_id)" class="flex justify-end">
          <UButton
            :label="`Practicar ${asked}`"
            icon="i-lucide-pen-line"
            color="neutral"
            variant="outline"
            size="sm"
            data-testid="review-practise"
            @click="practise"
          />
        </div>
      </div>
    </template>
  </UCollapsible>
</template>
