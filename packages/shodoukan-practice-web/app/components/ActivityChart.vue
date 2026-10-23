<script setup lang="ts">
import type { DayActivity } from '~/models/practice'

// Answers per day as bars, right ones (green) under wrong ones (red), scaled
// to the busiest day. Plain CSS; every bar has its figures as a tooltip and
// the chart has a text summary for screen readers.
const props = defineProps<{ days: DayActivity[] }>()

const max = computed(() => Math.max(1, ...props.days.map(d => d.answered)))
const total = computed(() => props.days.reduce((sum, d) => sum + d.answered, 0))
const active = computed(() => props.days.filter(d => d.answered > 0).length)

const dayFormat = new Intl.DateTimeFormat('es', { day: 'numeric', month: 'short', timeZone: 'UTC' })
function dayLabel(day: string) {
  return dayFormat.format(new Date(`${day}T00:00:00Z`))
}

function height(count: number) {
  return `${(count / max.value) * 100}%`
}

// Labels under the first, the middle and the last day.
const labelled = computed(() => new Set([0, Math.floor((props.days.length - 1) / 2), props.days.length - 1]))
</script>

<template>
  <figure class="space-y-2" data-testid="activity-chart">
    <div
      class="flex h-40 items-end gap-px sm:h-48 sm:gap-1"
      role="img"
      :aria-label="`${total} respuestas en ${days.length} días; ${active} días con actividad`"
    >
      <div
        v-for="day in days"
        :key="day.day"
        class="flex h-full min-w-0 flex-1 flex-col justify-end"
        :title="`${dayLabel(day.day)}: ${day.answered} respuestas, ${day.correct} acertadas`"
        data-testid="activity-day"
      >
        <div class="bg-error/70" :style="{ height: height(day.answered - day.correct) }" />
        <div class="rounded-b-sm bg-success" :style="{ height: height(day.correct) }" />
        <div v-if="!day.answered" class="h-px bg-accented" />
      </div>
    </div>
    <div class="flex text-xs text-dimmed">
      <span
        v-for="(day, index) in days"
        :key="day.day"
        class="min-w-0 flex-1 whitespace-nowrap"
        :class="index === days.length - 1 ? 'text-right' : index === 0 ? 'text-left' : 'text-center'"
      >
        <template v-if="labelled.has(index)">{{ dayLabel(day.day) }}</template>
      </span>
    </div>
    <figcaption class="flex gap-4 text-xs text-muted">
      <span class="flex items-center gap-1"><span class="size-2.5 rounded-sm bg-success" />Acertadas</span>
      <span class="flex items-center gap-1"><span class="size-2.5 rounded-sm bg-error/70" />Falladas</span>
    </figcaption>
  </figure>
</template>
