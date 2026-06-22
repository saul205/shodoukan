<script setup lang="ts">
const props = defineProps<{ literal: string }>()

interface CharData {
  strokes: string[]
  medians: [number, number][][]
}

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
  <div v-if="data" class="flex flex-wrap gap-1.5">
    <svg
      v-for="i in data.strokes.length"
      :key="i"
      viewBox="0 0 900 900"
      class="h-24 w-24 rounded border border-zinc-700 bg-zinc-800/60"
    >
      <line x1="450" y1="0" x2="450" y2="900" stroke="#3f3f46" stroke-width="3" stroke-dasharray="15 15" />
      <line x1="0" y1="450" x2="900" y2="450" stroke="#3f3f46" stroke-width="3" stroke-dasharray="15 15" />

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
    Stroke order not available.
  </p>

  <p v-else class="animate-pulse text-sm text-zinc-600">
    Loading stroke order…
  </p>
</template>
