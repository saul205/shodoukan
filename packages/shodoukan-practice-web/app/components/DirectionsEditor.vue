<script setup lang="ts">
import type { Direction, ItemKind, StudyField } from '~/models/practice'
import { FIELD_LABELS, STUDY_FIELDS } from '~/utils/study-fields'

// The rows "fields shown → field asked" of a card exercise. The answer is
// never offered among the shown fields: picking it as the answer takes it out
// of the prompt. Checking repeats and empty prompts is the form's job.
const props = defineProps<{ kind: ItemKind; disabled?: boolean }>()
const directions = defineModel<Direction[]>({ required: true })

const fields = computed(() => STUDY_FIELDS[props.kind])

function items(exclude?: StudyField) {
  return fields.value
    .filter(field => field !== exclude)
    .map(field => ({ label: FIELD_LABELS[field], value: field }))
}

function replace(index: number, direction: Direction) {
  directions.value = directions.value.map((current, i) => (i === index ? direction : current))
}

function setPrompt(index: number, prompt: StudyField[]) {
  replace(index, { ...directions.value[index]!, prompt })
}

function setAnswer(index: number, answer: StudyField) {
  const prompt = directions.value[index]!.prompt.filter(field => field !== answer)
  replace(index, { prompt, answer })
}

function add() {
  // A new row asks a field nothing else asks yet, shown with the first other one.
  const asked = new Set(directions.value.map(direction => direction.answer))
  const answer = fields.value.find(field => !asked.has(field)) ?? fields.value[0]!
  const prompt = fields.value.find(field => field !== answer)!
  directions.value = [...directions.value, { prompt: [prompt], answer }]
}

function remove(index: number) {
  directions.value = directions.value.filter((_, i) => i !== index)
}
</script>

<template>
  <div class="space-y-2">
    <div
      v-for="(direction, index) in directions"
      :key="index"
      class="flex flex-wrap items-center gap-2"
      data-testid="direction"
    >
      <USelectMenu
        :model-value="direction.prompt"
        :items="items(direction.answer)"
        value-key="value"
        multiple
        :search-input="false"
        :disabled="disabled"
        placeholder="Campos a mostrar"
        class="min-w-48 flex-1"
        :aria-label="`Campos que muestra la dirección ${index + 1}`"
        @update:model-value="setPrompt(index, $event as StudyField[])"
      />
      <UIcon name="i-lucide-arrow-right" class="size-4 shrink-0 text-muted" />
      <USelect
        :model-value="direction.answer"
        :items="items()"
        :disabled="disabled"
        class="w-40"
        :aria-label="`Campo que pregunta la dirección ${index + 1}`"
        data-testid="direction-answer"
        @update:model-value="setAnswer(index, $event as StudyField)"
      />
      <UButton
        icon="i-lucide-x"
        color="neutral"
        variant="ghost"
        :disabled="disabled"
        :aria-label="`Quitar la dirección ${index + 1}`"
        data-testid="remove-direction"
        @click="remove(index)"
      />
    </div>
    <UButton
      label="Añadir dirección"
      icon="i-lucide-plus"
      color="neutral"
      variant="outline"
      size="sm"
      :disabled="disabled"
      data-testid="add-direction"
      @click="add"
    />
  </div>
</template>
