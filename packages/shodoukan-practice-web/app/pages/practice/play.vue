<script setup lang="ts">
import { safeReturnPath } from '~/utils/return-path'
import { parseMode, parseRepetitions, practiceChars, type PracticeMode } from '~/utils/writing-practice'

// Writing practice of the characters in `?chars=` (`?mode=`, `?reps=`), so
// any page can link to it. `?from=` is where Volver goes (a path in this
// app); `/practice` by default.
const route = useRoute()
const router = useRouter()

const chars = computed(() => practiceChars(typeof route.query.chars === 'string' ? route.query.chars : ''))
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
      v-if="!chars.length"
      icon="i-lucide-pen-line"
      title="Nada que practicar"
      description="Elige qué practicar: kanji de tu librería o de una colección."
      :actions="[{ label: 'Elegir', to: '/practice', icon: 'i-lucide-arrow-right' }]"
    />

    <div v-else-if="finished" class="flex flex-1 flex-col items-center justify-center gap-4 text-center" data-testid="practice-finished">
      <UIcon name="i-lucide-circle-check" class="size-12 text-success" />
      <div>
        <p class="text-lg text-highlighted">Práctica terminada</p>
        <p class="text-muted">{{ chars.length === 1 ? '1 carácter' : `${chars.length} caracteres` }}</p>
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
      :chars="chars"
      :repetitions="repetitions"
      @finished="finished = true"
    />
  </AppPanel>
</template>
