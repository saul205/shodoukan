<script setup lang="ts">
// One figure with its label (and an optional detail below).
defineProps<{ label: string; value: string; detail?: string; icon?: string }>()
</script>

<template>
  <UCard :ui="{ body: 'p-4 sm:p-4' }" data-testid="stat-tile">
    <div class="flex items-center gap-2 text-xs uppercase tracking-wide text-dimmed">
      <UIcon v-if="icon" :name="icon" class="size-4" />
      {{ label }}
    </div>
    <p class="mt-1 text-2xl font-semibold text-highlighted tabular-nums sm:text-3xl" data-testid="stat-value">{{ value }}</p>
    <p v-if="detail" class="text-xs text-muted">{{ detail }}</p>
  </UCard>
</template>
