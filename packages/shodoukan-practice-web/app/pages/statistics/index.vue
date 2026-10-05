<script setup lang="ts">
import type { TableColumn, TableRow, TabsItem } from '@nuxt/ui'
import ItemDetailModal from '~/components/ItemDetailModal.vue'
import type { ExerciseSummary, ItemKind } from '~/models/practice'
import { getPracticeStatistics } from '~/services/statistics'
import { formatDateTime } from '~/utils/session-format'
import { ITEM_KIND_LABELS } from '~/utils/study-fields'

// "Estadísticas": how the user does over every exercise. Totals, the answers
// of each of the last days (?days=, in this browser's time zone), each
// exercise's figures (a row opens it) and the words and kanji missed most
// (?tab=). Sessions of deleted exercises count in the totals and the
// activity, not in the table.

const WINDOWS = [7, 30, 90]

const route = useRoute()
const router = useRouter()
const api = useApi()
const overlay = useOverlay()

const days = computed<number>({
  get: () => (WINDOWS.includes(Number(route.query.days)) ? Number(route.query.days) : 30),
  set: value => router.replace({ query: { ...route.query, days: value === 30 ? undefined : value } }),
})
const missedKind = computed<ItemKind>({
  get: () => (route.query.tab === 'kanji' ? 'kanji' : 'entries'),
  set: value => router.replace({ query: { ...route.query, tab: value === 'kanji' ? 'kanji' : undefined } }),
})

const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'

const { data: statistics, status, error } = useAsyncData(
  () => `practice-statistics-${days.value}`,
  () => getPracticeStatistics(api, days.value, timeZone),
  { watch: [days] },
)

const windowItems = WINDOWS.map(value => ({ label: `${value} días`, value }))
const missedTabs: TabsItem[] = [
  { label: 'Palabras', value: 'entries', icon: 'i-lucide-languages' },
  { label: 'Kanji', value: 'kanji', icon: 'i-lucide-type' },
]
const missed = computed(() =>
  missedKind.value === 'kanji' ? statistics.value?.most_missed_kanji ?? [] : statistics.value?.most_missed_entries ?? [],
)

const columns: TableColumn<ExerciseSummary>[] = [
  { accessorKey: 'exercise_name', header: 'Ejercicio' },
  { accessorKey: 'sessions', header: 'Sesiones' },
  { id: 'accuracy', header: 'Acierto' },
  { accessorKey: 'last_answered_at', header: 'Última vez' },
]

function openExercise(_event: Event, row: TableRow<ExerciseSummary>) {
  navigateTo(`/exercises/${row.original.exercise_id}`)
}

function openItem(itemId: number) {
  overlay.create(ItemDetailModal).open({ kind: missedKind.value, itemId, returnTo: route.fullPath })
}
</script>

<template>
  <AppPanel title="Estadísticas">
    <template #actions>
      <USelect v-model="days" :items="windowItems" class="w-32" aria-label="Periodo de la actividad" />
    </template>

    <div v-if="status === 'pending' && !statistics" class="space-y-3">
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <USkeleton v-for="i in 4" :key="i" class="h-24" />
      </div>
      <USkeleton class="h-56 w-full" />
    </div>

    <UAlert
      v-else-if="error"
      color="error"
      variant="soft"
      icon="i-lucide-circle-alert"
      title="No se han podido cargar tus estadísticas"
    />

    <UEmpty
      v-else-if="statistics && !statistics.totals.answered"
      icon="i-lucide-chart-column"
      title="Aún no hay nada que contar"
      description="Practica algún ejercicio y aquí verás cómo vas."
      :actions="[{ label: 'Ver tus ejercicios', icon: 'i-lucide-dumbbell', to: '/exercises' }]"
    />

    <div v-else-if="statistics" class="space-y-6">
      <TotalsTiles :totals="statistics.totals" />

      <UCard :ui="{ body: 'space-y-3' }">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-muted">Actividad · últimos {{ days }} días</h2>
        <ActivityChart :days="statistics.activity" />
      </UCard>

      <div class="grid gap-6 lg:grid-cols-5">
        <section aria-labelledby="by-exercise" class="space-y-3 lg:col-span-3">
          <h2 id="by-exercise" class="text-sm font-semibold uppercase tracking-wide text-muted">Por ejercicio</h2>
          <UTable
            :data="statistics.exercises"
            :columns="columns"
            :on-select="openExercise"
            class="rounded-md border border-default"
            :ui="{ tr: 'cursor-pointer' }"
            empty="Los ejercicios que practiques aparecerán aquí."
            data-testid="exercises-table"
          >
            <template #exercise_name-cell="{ row }">
              <span class="font-medium text-highlighted">{{ row.original.exercise_name }}</span>
              <UBadge :label="ITEM_KIND_LABELS[row.original.item_kind]" color="neutral" variant="subtle" size="sm" class="ml-2" />
            </template>
            <template #accuracy-cell="{ row }">
              <div class="w-32">
                <AccuracyBar label="" :correct="row.original.correct" :answered="row.original.answered" />
              </div>
            </template>
            <template #last_answered_at-cell="{ row }">
              {{ formatDateTime(row.original.last_answered_at) }}
            </template>
          </UTable>
        </section>

        <section aria-labelledby="missed" class="space-y-3 lg:col-span-2">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 id="missed" class="text-sm font-semibold uppercase tracking-wide text-muted">Los que más fallas</h2>
            <UTabs v-model="missedKind" :items="missedTabs" :content="false" size="sm" />
          </div>
          <UCard>
            <MissedItems :items="missed" @open-item="openItem" />
          </UCard>
        </section>
      </div>
    </div>
  </AppPanel>
</template>
