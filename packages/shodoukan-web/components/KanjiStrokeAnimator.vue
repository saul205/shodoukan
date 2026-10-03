<script setup lang="ts">
const props = defineProps<{ literal: string }>()

const container = ref<HTMLDivElement | null>(null)
const animating = ref(false)
const ready = ref(false)
let writer: any = null

onMounted(async () => {
  const HanziWriter = (await import('hanzi-writer')).default
  writer = (HanziWriter as any).create(container.value!, props.literal, {
    width: 160,
    height: 160,
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
      style="width: 160px; height: 160px;"
    />
    <button
      :disabled="!ready || animating"
      class="rounded bg-indigo-600/30 px-3 py-1 text-xs font-medium text-indigo-300 transition hover:bg-indigo-600/50 disabled:opacity-40"
      @click="play"
    >
      {{ animating ? 'Playing…' : 'Play' }}
    </button>
  </div>
</template>
