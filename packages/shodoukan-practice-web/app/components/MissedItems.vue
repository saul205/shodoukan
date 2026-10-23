<script setup lang="ts">
import type { MissedItem } from '~/models/practice'

// The items missed most: name (and reading), and how many of their answers
// were wrong. A row opens the item's detail.
defineProps<{ items: MissedItem[] }>()
defineEmits<{ 'open-item': [itemId: number] }>()
</script>

<template>
  <p v-if="!items.length" class="text-sm text-muted">Nada fallado todavía.</p>
  <ul v-else class="divide-y divide-default" data-testid="missed-items">
    <li v-for="item in items" :key="item.item_id">
      <button
        type="button"
        class="flex w-full items-center gap-3 px-1 py-2 text-left hover:bg-elevated/50"
        data-testid="missed-item"
        @click="$emit('open-item', item.item_id)"
      >
        <span class="min-w-0 flex-1 truncate">
          <span class="font-japanese text-lg text-highlighted">{{ item.label }}</span>
          <span v-if="item.reading" class="ml-2 font-japanese text-sm text-muted">{{ item.reading }}</span>
        </span>
        <span class="shrink-0 text-sm text-error tabular-nums">{{ item.wrong }} de {{ item.answered }}</span>
        <UIcon name="i-lucide-info" class="size-4 shrink-0 text-dimmed" />
      </button>
    </li>
  </ul>
</template>
