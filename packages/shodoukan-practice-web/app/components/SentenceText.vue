<script setup lang="ts">
// A sentence with some of its spans underlined: the words of a sentence,
// coloured by `tone` (`primary`: linked or marked; `warning`: to confirm;
// `neutral`: not linked). Spans don't overlap; one that does is skipped.

export interface TextSpan {
  start: number
  end: number
  tone: 'primary' | 'warning' | 'neutral'
}

const props = defineProps<{ text: string; spans: TextSpan[] }>()

const TONES: Record<TextSpan['tone'], string> = {
  primary: 'decoration-primary',
  warning: 'decoration-warning',
  neutral: 'decoration-dimmed decoration-dashed',
}

const pieces = computed(() => {
  const result: { text: string; tone: TextSpan['tone'] | null }[] = []
  let at = 0
  for (const span of [...props.spans].sort((a, b) => a.start - b.start)) {
    if (span.start < at) continue
    if (span.start > at) result.push({ text: props.text.slice(at, span.start), tone: null })
    result.push({ text: props.text.slice(span.start, span.end), tone: span.tone })
    at = span.end
  }
  if (at < props.text.length) result.push({ text: props.text.slice(at), tone: null })
  return result
})
</script>

<template>
  <span class="font-japanese">
    <template v-for="(piece, i) in pieces" :key="i">
      <span
        v-if="piece.tone"
        class="underline decoration-2 underline-offset-4"
        :class="TONES[piece.tone]"
        :data-tone="piece.tone"
      >{{ piece.text }}</span>
      <span v-else>{{ piece.text }}</span>
    </template>
  </span>
</template>
