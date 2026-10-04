<script setup lang="ts">
import { onMounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    literal: string
    unavailableLabel?: string
    loadingLabel?: string
    /** Smallest width of a stroke frame (CSS length); frames grow up to twice it. */
    cellSize?: string
  }>(),
  {
    unavailableLabel: 'Stroke order not available.',
    loadingLabel: 'Loading stroke order…',
    cellSize: '6rem',
  },
)

interface CharData {
  strokes: string[]
  medians: [number, number][][]
}

// The cell sizes go in inline styles: Tailwind 3 can't generate classes from a prop.

const data = ref<CharData | null>(null)
const failed = ref(false)

onMounted(async () => {
  try {
    const HanziWriter = (await import('hanzi-writer')).default
    data.value = await (HanziWriter as any).loadCharacterData(props.literal) as CharData
  }
  catch {
    failed.value = true
  }
})
</script>

<template>
  <div
    v-if="data"
    class="grid justify-center gap-1.5"
    :style="{ gridTemplateColumns: `repeat(auto-fit, minmax(${cellSize}, 1fr))` }"
  >
    <svg
      v-for="i in data.strokes.length"
      :key="i"
      viewBox="-64 -64 1152 1152"
      class="aspect-square w-full overflow-hidden rounded border border-zinc-700 bg-zinc-800/60"
      :style="{ maxWidth: `calc(${cellSize} * 2)` }"
    >
      <line x1="512" y1="0" x2="512" y2="1024" stroke="#3f3f46" stroke-width="3" stroke-dasharray="17 17" />
      <line x1="0" y1="512" x2="1024" y2="512" stroke="#3f3f46" stroke-width="3" stroke-dasharray="17 17" />

      <g transform="scale(1,-1) translate(0,-900)">
        <path
          v-for="j in i - 1"
          :key="j"
          :d="data.strokes[j - 1]"
          fill="#52525b"
        />
        <path
          :d="data.strokes[i - 1]"
          fill="#e4e4e7"
        />
        <circle
          :cx="data.medians[i - 1][0][0]"
          :cy="data.medians[i - 1][0][1]"
          r="40"
          fill="#ef4444"
        />
      </g>
    </svg>
  </div>

  <p v-else-if="failed" class="text-sm text-zinc-600">
    {{ unavailableLabel }}
  </p>

  <p v-else class="animate-pulse text-sm text-zinc-600">
    {{ loadingLabel }}
  </p>
</template>
