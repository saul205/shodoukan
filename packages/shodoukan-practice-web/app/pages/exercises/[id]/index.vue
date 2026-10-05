<script setup lang="ts">
import type { TableColumn, TableRow } from '@nuxt/ui'
import type { SessionSummary } from '~/models/practice'
import { listCollections } from '~/services/collections'
import { listSessions } from '~/services/exercise-sessions'
import { getExercise } from '~/services/exercises'
import { apiStatus } from '~/utils/api-error'
import { accuracyPercent, formatDateTime, formatDuration } from '~/utils/session-format'
import { directionLabel, FIELD_LABELS, ITEM_KIND_LABELS } from '~/utils/study-fields'

// One exercise: what it studies, "Empezar" (or "Continuar" if its session is
// the open one) and its session history, newest first, paged in the URL
// (?page=). A row opens the session: its review, or the session itself if
// it's still open.

const PAGE_SIZE = 10

const route = useRoute()
const router = useRouter()
const api = useApi()
const { start, starting } = useStartExercise()
const { session: openSession } = useOpenSession()

const id = computed(() => Number(route.params.id))
const page = computed<number>({
  get: () => Math.max(1, Number(route.query.page) || 1),
  set: value => router.push({ query: { ...route.query, page: value } }),
})

const { data: exercise, status, error } = useAsyncData(
  () => `exercise-${id.value}`,
  () => getExercise(api, id.value),
  { watch: [id] },
)

const { data: collections } = useAsyncData(
  () => `exercise-collections-${exercise.value?.item_kind}`,
  () => (exercise.value ? listCollections(api, exercise.value.item_kind) : Promise.resolve([])),
  { watch: [() => exercise.value?.item_kind] },
)
const collectionNames = computed(() => {
  const names = new Map((collections.value ?? []).map(c => [c.id, c.name]))
  return (exercise.value?.collection_ids ?? []).map(cid => names.get(cid) ?? `#${cid}`)
})

const { data: history, status: historyStatus } = useAsyncData(
  () => `exercise-history-${id.value}-${page.value}`,
  () => listSessions(api, { exercise_id: id.value, limit: PAGE_SIZE, offset: (page.value - 1) * PAGE_SIZE }),
  { watch: [id, page] },
)

const resumable = computed(() => (openSession.value?.exercise_id === id.value ? openSession.value : null))

const columns: TableColumn<SessionSummary>[] = [
  { accessorKey: 'started_at', header: 'Fecha' },
  { id: 'duration', header: 'Duración' },
  { accessorKey: 'answered', header: 'Respondidas' },
  { id: 'accuracy', header: 'Acierto' },
  { id: 'status', header: 'Estado' },
]

function openSessionRow(_event: Event, row: TableRow<SessionSummary>) {
  navigateTo(`/exercise-sessions/${row.original.id}`)
}
</script>

<template>
  <AppPanel :title="exercise?.name ?? 'Ejercicio'">
    <template #leading>
      <UButton to="/exercises" icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver a los ejercicios" />
    </template>
    <template v-if="exercise" #actions>
      <UButton :to="`/exercises/${exercise.id}/edit`" label="Editar" icon="i-lucide-pencil" color="neutral" variant="ghost" />
      <UButton
        v-if="resumable"
        :to="`/exercise-sessions/${resumable.id}`"
        label="Continuar"
        icon="i-lucide-arrow-right"
        data-testid="resume"
      />
      <UButton
        v-else
        label="Empezar"
        icon="i-lucide-play"
        :disabled="!exercise.collection_ids.length"
        :loading="starting"
        data-testid="start"
        @click="start(exercise)"
      />
    </template>

    <USkeleton v-if="status === 'pending' && !exercise" class="h-64 w-full" />

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

    <div v-else-if="exercise" class="space-y-8">
      <UCard :ui="{ body: 'space-y-3' }" data-testid="definition">
        <p v-if="exercise.description" class="text-muted">{{ exercise.description }}</p>
        <div class="flex flex-wrap gap-1">
          <UBadge :label="ITEM_KIND_LABELS[exercise.item_kind]" color="primary" variant="subtle" />
          <UBadge
            v-for="name in collectionNames"
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
        <dl class="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[auto_1fr]">
          <dt class="text-dimmed">Direcciones</dt>
          <dd class="text-toned">
            <span v-for="direction in exercise.settings.directions" :key="directionLabel(direction)" class="block">
              {{ directionLabel(direction) }}
            </span>
          </dd>
          <dt class="text-dimmed">Reverso</dt>
          <dd class="text-toned">
            {{ exercise.settings.back_fields.map(field => FIELD_LABELS[field]).join(', ') || 'Solo la pregunta y la respuesta' }}
          </dd>
          <dt class="text-dimmed">Opciones</dt>
          <dd class="text-toned">{{ exercise.settings.option_count }} por tarjeta</dd>
        </dl>
      </UCard>

      <section aria-labelledby="history" class="space-y-3">
        <h2 id="history" class="text-sm font-semibold uppercase tracking-wide text-muted">Historial</h2>

        <UEmpty
          v-if="historyStatus === 'success' && !history?.total"
          icon="i-lucide-history"
          title="Aún no has practicado este ejercicio"
          description="Cada sesión que hagas quedará aquí, con su resultado y su repaso."
        />

        <template v-else>
          <UTable
            :data="history?.items ?? []"
            :columns="columns"
            :loading="historyStatus === 'pending'"
            :on-select="openSessionRow"
            class="rounded-md border border-default"
            :ui="{ tr: 'cursor-pointer' }"
            data-testid="history"
          >
            <template #started_at-cell="{ row }">
              {{ formatDateTime(row.original.started_at) }}
            </template>
            <template #duration-cell="{ row }">
              {{ formatDuration(row.original.started_at, row.original.finished_at ?? row.original.last_activity_at) }}
            </template>
            <template #accuracy-cell="{ row }">
              <template v-if="accuracyPercent(row.original.score, row.original.answered) !== null">
                {{ accuracyPercent(row.original.score, row.original.answered) }}%
                <span class="text-dimmed">({{ row.original.score }}/{{ row.original.answered }})</span>
              </template>
              <span v-else class="text-dimmed">—</span>
            </template>
            <template #status-cell="{ row }">
              <UBadge
                :label="row.original.finished_at ? 'Terminada' : 'Abierta'"
                :color="row.original.finished_at ? 'neutral' : 'primary'"
                variant="subtle"
              />
            </template>
          </UTable>
          <UPagination
            v-if="(history?.total ?? 0) > PAGE_SIZE"
            v-model:page="page"
            :total="history?.total ?? 0"
            :items-per-page="PAGE_SIZE"
            class="flex justify-center"
          />
        </template>
      </section>
    </div>
  </AppPanel>
</template>
