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
  <div v-if="data" class="grid grid-cols-[repeat(auto-fit,minmax(6rem,1fr))] justify-center gap-1.5">
    <svg
      v-for="i in data.strokes.length"
      :key="i"
      viewBox="-64 -64 1152 1152"
      class="aspect-square w-full max-w-[12rem] overflow-hidden rounded border border-zinc-700 bg-zinc-800/60"
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
    Stroke order not available.
  </p>

  <p v-else class="animate-pulse text-sm text-zinc-600">
    Loading stroke order…
  </p>
</template>
