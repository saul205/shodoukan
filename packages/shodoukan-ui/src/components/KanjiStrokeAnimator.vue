<script setup lang="ts">
import { onMounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    literal: string
    playLabel?: string
    playingLabel?: string
    /** Width and height of the drawing, in px. */
    size?: number
  }>(),
  { playLabel: 'Play', playingLabel: 'Playing…', size: 160 },
)

const container = ref<HTMLDivElement | null>(null)
const animating = ref(false)
const ready = ref(false)
let writer: any = null

onMounted(async () => {
  const HanziWriter = (await import('hanzi-writer')).default
  writer = (HanziWriter as any).create(container.value!, props.literal, {
    width: props.size,
    height: props.size,
    padding: 8,
    showOutline: true,
    showCharacter: false,
    strokeColor: '#e4e4e7',
    outlineColor: '#3f3f46',
    delayBetweenStrokes: 250,
    strokeAnimationSpeed: 1.2,
  })
  ready.value = true
})

function play() {
  if (animating.value || !writer) return
  animating.value = true
  writer.hideCharacter()
  writer.animateCharacter({
    onComplete() {
      animating.value = false
    },
  })
}
</script>

<template>
  <div class="flex flex-col items-center gap-2">
    <div
      ref="container"
      class="rounded border border-zinc-700 bg-zinc-800/60"
      :style="{ width: `${size}px`, height: `${size}px` }"
    />
    <button
      :disabled="!ready || animating"
      class="rounded bg-indigo-600/30 px-3 py-1 text-xs font-medium text-indigo-300 transition hover:bg-indigo-600/50 disabled:opacity-40"
      @click="play"
    >
      {{ animating ? playingLabel : playLabel }}
    </button>
  </div>
</template>
