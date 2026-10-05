<script setup lang="ts">
import type { ChoiceOption } from '~/models/practice'

// The options of a choice card, numbered for the keyboard, all the same size:
// rows of equal height (the tallest option's), in two columns. Phones get one
// column, easier to read and tap, unless the texts are short (two big boxes
// per row read better) or it wouldn't fit the screen: 7–8 options, or 5–6 on
// a short screen (see `columns`). Very long texts
// are cut at three lines (the whole text is the tooltip). Once answered
// (`correct` known), the right one turns green and the picked one, if wrong,
// red; options that came from an item get a detail button in their corner, so
// nothing moves. `compact` is the smaller list of a session review.
const props = defineProps<{
  options: ChoiceOption[]
  picked: number | null
  correct: number | null
  japanese?: boolean
  disabled?: boolean
  compact?: boolean
}>()
const emit = defineEmits<{ 'pick': [index: number]; 'open-item': [itemId: number] }>()

const answered = computed(() => props.correct !== null)

// Short enough for half a phone's width: a kanji, a kana word, "eat".
const SHORT_TEXT = { japanese: 6, other: 12 }
const short = computed(() => {
  const limit = props.japanese ? SHORT_TEXT.japanese : SHORT_TEXT.other
  return props.options.every(option => option.text.length <= limit)
})

const columns = computed(() => {
  if (props.compact) return 'grid-cols-1 sm:grid-cols-2'
  const count = props.options.length
  if (count >= 7 || short.value) return 'grid-cols-2'
  if (count >= 5) return 'grid-cols-1 sm:grid-cols-2 [@media(max-height:40rem)]:grid-cols-2'
  return 'grid-cols-1 sm:grid-cols-2'
})

function color(index: number) {
  if (!answered.value) return 'neutral'
  if (index === props.correct) return 'success'
  if (index === props.picked) return 'error'
  return 'neutral'
}

function state(index: number) {
  if (!answered.value) return undefined
  if (index === props.correct) return 'correct'
  if (index === props.picked) return 'wrong'
  return 'other'
}
</script>

<template>
  <div class="grid auto-rows-fr gap-2 sm:gap-3" :class="columns" data-testid="options">
    <div v-for="(option, index) in options" :key="index" class="relative">
      <UButton
        :color="color(index)"
        :variant="answered && state(index) !== 'other' ? 'soft' : 'outline'"
        :disabled="disabled && !answered"
        :size="compact ? 'md' : 'xl'"
        class="h-full w-full justify-center px-8 text-center whitespace-normal sm:px-10"
        :class="[
          compact ? 'min-h-10' : 'min-h-12 sm:min-h-16',
          { 'opacity-60': state(index) === 'other', 'pointer-events-none': answered },
        ]"
        :title="option.text"
        :aria-pressed="picked === index"
        :data-state="state(index)"
        data-option-shortcuts
        data-testid="option"
        @click="answered || emit('pick', index)"
      >
        <UKbd v-if="!compact" :value="String(index + 1)" class="absolute top-1/2 left-3 hidden -translate-y-1/2 sm:inline-flex" />
        <span
          class="line-clamp-3"
          :class="compact
            ? (japanese ? 'font-japanese text-base' : 'text-sm')
            : (japanese ? 'font-japanese text-lg sm:text-xl lg:text-2xl' : 'text-base sm:text-lg lg:text-xl')"
        >{{ option.text }}</span>
      </UButton>
      <UButton
        v-if="answered && option.item_id !== null"
        icon="i-lucide-info"
        color="neutral"
        variant="ghost"
        size="xs"
        class="absolute top-1 right-1"
        :aria-label="`Ver el detalle de ${option.text}`"
        data-testid="open-option-item"
        @click="emit('open-item', option.item_id)"
      />
    </div>
  </div>
</template>
