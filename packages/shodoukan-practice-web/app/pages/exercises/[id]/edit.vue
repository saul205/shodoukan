<script setup lang="ts">
import type { Exercise } from '~/models/practice'
import { getExercise } from '~/services/exercises'
import { apiStatus } from '~/utils/api-error'

const route = useRoute()
const api = useApi()
const notify = useNotify()

const id = computed(() => Number(route.params.id))
const { data: exercise, status, error } = useAsyncData(
  () => `exercise-${id.value}`,
  () => getExercise(api, id.value),
  { watch: [id] },
)

async function onSaved(saved: Exercise) {
  notify.success(`Ejercicio «${saved.name}» guardado`)
  await navigateTo('/exercises')
}
</script>

<template>
  <AppPanel :title="exercise ? `Editar «${exercise.name}»` : 'Editar ejercicio'">
    <template #leading>
      <UButton to="/exercises" icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver a los ejercicios" />
    </template>

    <USkeleton v-if="status === 'pending' && !exercise" class="h-96 max-w-3xl" />

    <UEmpty
      v-else-if="apiStatus(error) === 404"
      icon="i-lucide-search-x"
      title="Este ejercicio no existe"
      :actions="[{ label: 'Ver tus ejercicios', to: '/exercises' }]"
    />

    <UAlert
      v-else-if="error"
      color="error"
      variant="soft"
      icon="i-lucide-circle-alert"
      title="No se ha podido cargar el ejercicio"
    />

    <UCard v-else-if="exercise" class="max-w-3xl">
      <ExerciseForm :key="exercise.id" :exercise="exercise" @saved="onSaved" />
    </UCard>
  </AppPanel>
</template>
