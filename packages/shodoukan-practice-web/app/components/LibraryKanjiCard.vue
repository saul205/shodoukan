<script setup lang="ts">
import type { PracticeKanji } from '~/models/practice'
import { kanjiMeanings } from '~/utils/practice-text'

// A kanji of the user's library, as a card that opens its detail page.
const props = defineProps<{ kanji: PracticeKanji; to: string }>()

const { lang } = useMeaningLang()

const meanings = computed(() => kanjiMeanings(props.kanji, lang.value).slice(0, 4).join(', '))
const readings = computed(() =>
  [...props.kanji.kun_readings, ...props.kanji.on_readings]
    .filter(r => r.enabled)
    .slice(0, 4)
    .map(r => r.text)
    .join('、'),
)
</script>

<template>
  <UCard
    :ui="{ body: 'p-4 sm:p-4 h-full flex flex-col gap-2' }"
    class="h-full transition hover:ring-accented"
    :class="{ 'opacity-60': !kanji.is_active }"
  >
    <NuxtLink :to="to" class="flex flex-1 items-start gap-3">
      <span class="font-japanese text-4xl font-bold text-highlighted">{{ kanji.literal }}</span>
      <span class="flex min-w-0 flex-col gap-1">
        <span class="line-clamp-2 text-sm text-toned">{{ meanings || '—' }}</span>
        <span class="truncate font-japanese text-xs text-muted">{{ readings }}</span>
      </span>
    </NuxtLink>
    <div class="flex flex-wrap items-center gap-1">
      <UBadge v-if="kanji.jlpt" :label="`N${kanji.jlpt}`" variant="soft" size="sm" />
      <UBadge v-if="!kanji.is_active" label="inactivo" color="neutral" variant="outline" size="sm" />
      <UIcon v-if="kanji.notes" name="i-lucide-sticky-note" class="size-4 text-muted" />
      <div class="ms-auto">
        <slot name="actions" />
      </div>
    </div>
  </UCard>
</template>
