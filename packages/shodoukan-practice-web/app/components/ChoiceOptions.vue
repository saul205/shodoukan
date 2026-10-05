<script setup lang="ts">
import type { ChoiceOption } from '~/models/practice'

// The options of a choice card, numbered for the keyboard, all the same size:
// rows of equal height (the tallest option's, at least two lines), one column
// on phones and two above. Very long texts are cut at three lines (the whole
// text is the tooltip). Once answered (`correct` known), the right one turns
// green and the picked one, if wrong, red; options that came from an item get
// a detail button in their corner, so nothing moves.
const props = defineProps<{
  options: ChoiceOption[]
  picked: number | null
  correct: number | null
  japanese?: boolean
  disabled?: boolean
}>()
const emit = defineEmits<{ 'pick': [index: number]; 'open-item': [itemId: number] }>()

const answered = computed(() => props.correct !== null)

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
  <div class="grid auto-rows-fr grid-cols-1 gap-2 sm:grid-cols-2 sm:gap-3">
    <div v-for="(option, index) in options" :key="index" class="relative">
      <UButton
        :color="color(index)"
        :variant="answered && state(index) !== 'other' ? 'soft' : 'outline'"
        :disabled="disabled && !answered"
        size="xl"
        class="h-full min-h-14 w-full justify-center px-10 text-center whitespace-normal sm:min-h-16"
        :class="{ 'opacity-60': state(index) === 'other', 'pointer-events-none': answered }"
        :title="option.text"
        :aria-pressed="picked === index"
        :data-state="state(index)"
        data-option-shortcuts
        data-testid="option"
        @click="answered || emit('pick', index)"
      >
        <UKbd :value="String(index + 1)" class="absolute top-1/2 left-3 hidden -translate-y-1/2 sm:inline-flex" />
        <span
          class="line-clamp-3"
          :class="japanese ? 'font-japanese text-lg sm:text-xl lg:text-2xl' : 'text-base sm:text-lg lg:text-xl'"
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
