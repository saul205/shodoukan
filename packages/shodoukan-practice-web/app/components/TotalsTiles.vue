<script setup lang="ts">
import type { AnswerTotals } from '~/models/practice'
import { formatResponseTime } from '~/utils/session-format'

// The four headline figures: sessions, answers, accuracy and mean time.
const props = defineProps<{ totals: AnswerTotals }>()

const accuracy = computed(() =>
  props.totals.accuracy === null ? '—' : `${Math.round(props.totals.accuracy * 100)}%`,
)
const meanTime = computed(() =>
  props.totals.mean_response_ms === null ? '—' : formatResponseTime(props.totals.mean_response_ms),
)
</script>

<template>
  <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
    <StatTile label="Sesiones" :value="String(totals.sessions)" icon="i-lucide-calendar-check" />
    <StatTile label="Respuestas" :value="String(totals.answered)" icon="i-lucide-list-checks" />
    <StatTile
      label="Acierto"
      :value="accuracy"
      :detail="totals.answered ? `${totals.correct} de ${totals.answered}` : undefined"
      icon="i-lucide-target"
    />
    <StatTile label="Tiempo medio" :value="meanTime" icon="i-lucide-timer" />
  </div>
</template>
