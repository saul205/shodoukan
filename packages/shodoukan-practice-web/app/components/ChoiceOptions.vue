<script setup lang="ts">
import type { ChoiceOption } from '~/models/practice'

// The options of a choice card, numbered for the keyboard. Once answered
// (`correct` known), the right one turns green and the picked one, if wrong,
// red; options that came from an item can open its detail.
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
  <div class="grid gap-2 sm:grid-cols-2">
    <div v-for="(option, index) in options" :key="index" class="flex items-center gap-1">
      <UButton
        :color="color(index)"
        :variant="answered && state(index) !== 'other' ? 'soft' : 'outline'"
        :disabled="disabled && !answered"
        size="xl"
        block
        class="justify-start"
        :class="{ 'opacity-60': state(index) === 'other', 'pointer-events-none': answered }"
        :aria-pressed="picked === index"
        :data-state="state(index)"
        data-testid="option"
        @click="answered || emit('pick', index)"
      >
        <UKbd :value="String(index + 1)" class="mr-1" />
        <span :class="{ 'font-japanese': japanese }">{{ option.text }}</span>
      </UButton>
      <UButton
        v-if="answered && option.item_id !== null"
        icon="i-lucide-info"
        color="neutral"
        variant="ghost"
        size="sm"
        :aria-label="`Ver el detalle de ${option.text}`"
        data-testid="open-option-item"
        @click="emit('open-item', option.item_id)"
      />
    </div>
  </div>
</template>
