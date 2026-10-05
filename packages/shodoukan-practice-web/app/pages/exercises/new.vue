<script setup lang="ts">
import type { Exercise } from '~/models/practice'

const notify = useNotify()

async function onSaved(exercise: Exercise) {
  notify.success(`Ejercicio «${exercise.name}» creado`)
  await navigateTo('/exercises')
}
</script>

<template>
  <AppPanel title="Nuevo ejercicio">
    <template #leading>
      <UButton to="/exercises" icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver a los ejercicios" />
    </template>

    <UCard class="max-w-3xl">
      <ExerciseForm @saved="onSaved" />
    </UCard>
  </AppPanel>
</template>
