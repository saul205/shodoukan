<script setup lang="ts">
// A labelled accuracy bar: right answers over answers, with the figures.
// Green from 80%, amber from 50%, red below.
const props = defineProps<{ label: string; correct: number; answered: number }>()

const percent = computed(() => (props.answered ? Math.round((props.correct / props.answered) * 100) : 0))
const color = computed(() => (percent.value >= 80 ? 'success' : percent.value >= 50 ? 'warning' : 'error'))
</script>

<template>
  <div class="space-y-1" data-testid="accuracy-bar">
    <div class="flex items-baseline justify-between gap-3 text-sm">
      <span class="truncate text-default">{{ label }}</span>
      <span class="shrink-0 text-muted tabular-nums">{{ percent }}% · {{ correct }}/{{ answered }}</span>
    </div>
    <UProgress :model-value="percent" :max="100" :color="color" size="sm" />
  </div>
</template>
