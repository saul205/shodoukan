<script setup lang="ts">
import { safeReturnPath } from '~/utils/return-path'
import {
  parseIds,
  parseMode,
  parseRepetitions,
  practiceChars,
  type PracticeItem,
  type PracticeMode,
} from '~/utils/writing-practice'

// Writing practice of the library kanji in `?kanji=12,15`, the library words
// in `?entries=3,4`, or the characters in `?chars=` (kana, or kanji linked
// without an id), with `?mode=` and `?reps=`, so any page can link to it.
// `?from=` is where Volver goes (a path in this app); `/practice` by default.
const route = useRoute()
const router = useRouter()

const items = computed<PracticeItem[]>(() => {
  if (route.query.kanji) return parseIds(route.query.kanji).map(id => ({ kind: 'kanji', id }))
  if (route.query.entries) return parseIds(route.query.entries).map(id => ({ kind: 'entry', id }))
  return practiceChars(typeof route.query.chars === 'string' ? route.query.chars : '').map(text => ({ kind: 'char', text }))
})
const countLabel = computed(() => {
  const n = items.value.length
  if (route.query.entries) return n === 1 ? '1 palabra' : `${n} palabras`
  return n === 1 ? '1 carácter' : `${n} caracteres`
})
const mode = computed<PracticeMode>({
  get: () => parseMode(route.query.mode),
  set: value => router.replace({ query: { ...route.query, mode: value } }),
})
const repetitions = computed(() => parseRepetitions(route.query.reps))
const back = computed(() => (typeof route.query.from === 'string' ? safeReturnPath(route.query.from) : '/practice'))

const finished = ref(false)
const run = ref(0)

function again() {
  finished.value = false
  run.value++
}
</script>

<template>
  <AppPanel title="Practicar escritura" fill>
    <template #leading>
      <UButton :to="back" icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver" />
    </template>

    <UEmpty
      v-if="!items.length"
      icon="i-lucide-pen-line"
      title="Nada que practicar"
      description="Elige qué practicar: kanji, palabras o kana."
      :actions="[{ label: 'Elegir', to: '/practice', icon: 'i-lucide-arrow-right' }]"
    />

    <div v-else-if="finished" class="flex flex-1 flex-col items-center justify-center gap-4 text-center" data-testid="practice-finished">
      <UIcon name="i-lucide-circle-check" class="size-12 text-success" />
      <div>
        <p class="text-lg text-highlighted">Práctica terminada</p>
        <p class="text-muted">{{ countLabel }}</p>
      </div>
      <div class="flex gap-2">
        <UButton label="Otra vez" icon="i-lucide-rotate-ccw" color="neutral" variant="outline" @click="again" />
        <UButton :to="back" label="Volver" />
      </div>
    </div>

    <WritingPractice
      v-else
      :key="run"
      v-model:mode="mode"
      :items="items"
      :repetitions="repetitions"
      @finished="finished = true"
    />
  </AppPanel>
</template>
