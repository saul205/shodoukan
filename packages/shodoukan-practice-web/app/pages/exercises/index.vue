<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import ConfirmModal from '~/components/ConfirmModal.vue'
import type { Exercise } from '~/models/practice'
import { listCollections } from '~/services/collections'
import { deleteExercise, listExercises } from '~/services/exercises'
import { directionLabel, ITEM_KIND_LABELS } from '~/utils/study-fields'

// "Ejercicios": the user's saved exercises, with what each studies and the
// collections it draws from; create, edit and delete them.

const api = useApi()
const notify = useNotify()
const overlay = useOverlay()
const confirm = overlay.create(ConfirmModal)
const { start, starting } = useStartExercise()

const { data, status, error, refresh } = useAsyncData('exercises', async () => {
  const [exercises, entryCollections, kanjiCollections] = await Promise.all([
    listExercises(api),
    listCollections(api, 'entries'),
    listCollections(api, 'kanji'),
  ])
  return {
    exercises,
    names: {
      entries: new Map(entryCollections.map(collection => [collection.id, collection.name])),
      kanji: new Map(kanjiCollections.map(collection => [collection.id, collection.name])),
    },
  }
})

function collectionNames(exercise: Exercise): string[] {
  const names = data.value?.names[exercise.item_kind]
  return exercise.collection_ids.map(id => names?.get(id) ?? `#${id}`)
}

async function remove(exercise: Exercise) {
  const confirmed = await confirm.open({
    title: `¿Eliminar «${exercise.name}»?`,
    description: 'Sus sesiones pasadas se conservan en el historial.',
  }).result
  if (!confirmed) return
  try {
    await deleteExercise(api, exercise.id)
    notify.success('Ejercicio eliminado')
    await refresh()
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido eliminar')
  }
}

function actions(exercise: Exercise): DropdownMenuItem[][] {
  return [
    [{ label: 'Editar', icon: 'i-lucide-pencil', to: `/exercises/${exercise.id}/edit` }],
    [{ label: 'Eliminar', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => remove(exercise) }],
  ]
}
</script>

<template>
  <AppPanel title="Ejercicios">
    <template #actions>
      <UButton label="Nuevo ejercicio" icon="i-lucide-plus" to="/exercises/new" />
    </template>

    <OpenSessionAlert class="mb-5" />

    <div v-if="status === 'pending' && !data" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <USkeleton v-for="i in 3" :key="i" class="h-32" />
    </div>

    <UAlert
      v-else-if="error"
      color="error"
      variant="soft"
      icon="i-lucide-circle-alert"
      title="No se han podido cargar tus ejercicios"
    />

    <UEmpty
      v-else-if="!data?.exercises.length"
      icon="i-lucide-dumbbell"
      title="Aún no tienes ejercicios"
      description="Un ejercicio dice qué colecciones estudiar y cómo: qué se muestra en la tarjeta y qué se pregunta."
      :actions="[{ label: 'Nuevo ejercicio', icon: 'i-lucide-plus', to: '/exercises/new' }]"
    />

    <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <UCard
        v-for="exercise in data.exercises"
        :key="exercise.id"
        :ui="{ body: 'p-4 sm:p-4 space-y-3' }"
        data-testid="exercise"
      >
        <div class="flex items-start gap-3">
          <div class="min-w-0 flex-1">
            <NuxtLink :to="`/exercises/${exercise.id}`" class="block truncate font-medium text-highlighted hover:underline">
              {{ exercise.name }}
            </NuxtLink>
            <p v-if="exercise.description" class="line-clamp-2 text-sm text-muted">{{ exercise.description }}</p>
          </div>
          <UDropdownMenu :items="actions(exercise)" :content="{ align: 'end' }">
            <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" size="sm" aria-label="Acciones" />
          </UDropdownMenu>
        </div>

        <div class="flex flex-wrap gap-1">
          <UBadge :label="ITEM_KIND_LABELS[exercise.item_kind]" color="primary" variant="subtle" />
          <UBadge
            v-for="name in collectionNames(exercise)"
            :key="name"
            :label="name"
            color="neutral"
            variant="outline"
            icon="i-lucide-folder"
          />
          <UBadge
            v-if="!exercise.collection_ids.length"
            label="Sin colecciones"
            color="warning"
            variant="subtle"
            icon="i-lucide-triangle-alert"
          />
        </div>

        <ul class="space-y-0.5 text-sm text-muted">
          <li v-for="direction in exercise.settings.directions" :key="directionLabel(direction)">
            {{ directionLabel(direction) }}
          </li>
        </ul>

        <UButton
          label="Empezar"
          icon="i-lucide-play"
          block
          :disabled="!exercise.collection_ids.length || starting"
          data-testid="start"
          @click="start(exercise)"
        />
      </UCard>
    </div>
  </AppPanel>
</template>
