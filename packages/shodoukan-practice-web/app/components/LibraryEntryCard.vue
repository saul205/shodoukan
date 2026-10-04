<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'
import type { PracticeEntry } from '~/models/practice'
import { entryHeadword, entryMeanings, entryReading } from '~/utils/practice-text'

// A word of the user's library, as a card that opens its detail page.
const props = defineProps<{ entry: PracticeEntry; to: RouteLocationRaw }>()

const { glossCode } = useMeaningLang()

const meanings = computed(() => entryMeanings(props.entry, glossCode.value).slice(0, 4).join(' · '))
</script>

<template>
  <UCard
    :ui="{ body: 'p-4 sm:p-4 h-full flex flex-col gap-2' }"
    class="h-full transition hover:ring-accented"
    :class="{ 'opacity-60': !entry.is_active }"
  >
    <NuxtLink :to="to" class="flex flex-1 flex-col gap-1">
      <span v-if="entryReading(entry)" class="font-japanese text-xs text-muted">{{ entryReading(entry) }}</span>
      <span class="font-japanese text-xl font-bold text-highlighted">{{ entryHeadword(entry) }}</span>
      <span class="line-clamp-2 text-sm text-toned">{{ meanings || '—' }}</span>
    </NuxtLink>
    <div class="flex flex-wrap items-center gap-1">
      <UBadge v-if="entry.jlpt" :label="`N${entry.jlpt}`" variant="soft" size="sm" />
      <UBadge v-if="entry.is_common" label="común" color="success" variant="soft" size="sm" />
      <UBadge v-if="!entry.is_active" label="inactiva" color="neutral" variant="outline" size="sm" />
      <UIcon v-if="entry.notes" name="i-lucide-sticky-note" class="size-4 text-muted" />
      <div class="ms-auto">
        <slot name="actions" />
      </div>
    </div>
  </UCard>
</template>
