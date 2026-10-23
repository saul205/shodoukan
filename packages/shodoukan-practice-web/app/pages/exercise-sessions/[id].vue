<script setup lang="ts">
import ItemDetailModal from '~/components/ItemDetailModal.vue'
import { PLAYERS } from '~/components/exercise-players'
import type { ExerciseAnswer, ExerciseQuestion } from '~/models/practice'
import { answerQuestion, finishSession, getSession } from '~/services/exercise-sessions'
import { getExercise } from '~/services/exercises'
import { apiStatus } from '~/utils/api-error'
import { formatDateTime, formatDuration } from '~/utils/session-format'

// Play a session: one question at a time, picked by its type's player.
// Answering shows the graded card; "Siguiente" shows the next one, which the
// answer already brought. A finished session shows its result and a review
// of every answered question as it was played (?filter=missed: only the
// missed and skipped ones).

const route = useRoute()
const router = useRouter()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()
const { start, starting } = useStartExercise()

const id = computed(() => Number(route.params.id))
const { data: session, status, error, refresh } = useAsyncData(
  () => `exercise-session-${id.value}`,
  () => getSession(api, id.value),
  { watch: [id] },
)

// On screen: the active question, or the one just answered (with its
// solution) while `next` waits for "Siguiente". `next` undefined: not
// answered yet; null: no other question could be made.
const question = ref<ExerciseQuestion | null>(null)
const next = ref<ExerciseQuestion | null | undefined>(undefined)
const answered = ref(0)
const score = ref(0)
const busy = ref(false)
const finishing = ref(false)
// Set when an answer finished the session (its exercise was deleted).
const closedByAnswer = ref(false)

watch(session, (value) => {
  question.value = value?.current ?? null
  next.value = undefined
  closedByAnswer.value = false
  answered.value = value?.answered ?? 0
  score.value = value?.score ?? 0
}, { immediate: true })

// The exercise's back fields, so the card keeps room for its back before
// answering. None if the exercise was deleted, or while (or if failing) loading;
// not loaded for a finished session, which has no card to play.
const exerciseId = computed(() =>
  session.value && !session.value.finished_at ? session.value.exercise_id : null,
)
const { data: exercise } = useAsyncData(
  () => `exercise-session-exercise-${exerciseId.value}`,
  () => (exerciseId.value === null ? Promise.resolve(null) : getExercise(api, exerciseId.value)),
  { watch: [exerciseId] },
)
const backFields = computed(() => exercise.value?.settings?.back_fields ?? [])

const finished = computed(() => !!session.value?.finished_at)
const exhausted = computed(() => !finished.value && !question.value)
const player = computed(() => (question.value ? PLAYERS[question.value.type] : null))
// Back to the exercise, or to the list if it was deleted.
const back = computed(() =>
  session.value?.exercise_id != null
    ? { to: `/exercises/${session.value.exercise_id}`, label: 'Volver al ejercicio' }
    : { to: '/exercises', label: 'Volver a los ejercicios' },
)

const onlyMissed = computed<boolean>({
  get: () => route.query.filter === 'missed',
  set: value => router.replace({ query: { ...route.query, filter: value ? 'missed' : undefined } }),
})
const missedCount = computed(() => session.value?.history.filter(q => !q.is_correct).length ?? 0)
const reviewed = computed(() =>
  (session.value?.history ?? []).filter(q => !onlyMissed.value || !q.is_correct),
)
// Which review questions are open, by id; all start collapsed. Kept per
// session for the app's lifetime, so going to an item's library page and
// back keeps them open (the filter is in the URL).
const expandedBySession = useState<Record<number, Record<number, boolean>>>('session-review-expanded', () => ({}))
const expanded = computed<Record<number, boolean>>({
  get: () => (expandedBySession.value[id.value] ??= {}),
  set: value => (expandedBySession.value[id.value] = value),
})
const allExpanded = computed(() => reviewed.value.length > 0 && reviewed.value.every(q => expanded.value[q.id]))
function expandAll(open: boolean) {
  expanded.value = Object.fromEntries(reviewed.value.map(q => [q.id, open]))
}

const reviewTabs = computed(() => [
  { label: `Todas (${session.value?.history.length ?? 0})`, value: 'all' },
  { label: `Falladas (${missedCount.value})`, value: 'missed' },
])

const accuracy = computed(() => (answered.value ? Math.round((score.value / answered.value) * 100) : null))

async function onAnswer(answer: ExerciseAnswer, responseMs: number) {
  if (!question.value) return
  busy.value = true
  try {
    const result = await answerQuestion(api, id.value, question.value.id, answer, responseMs)
    question.value = result.answered
    next.value = result.next
    answered.value = result.answered_count
    score.value = result.score
    closedByAnswer.value = result.finished_at !== null
  }
  catch (failure) {
    if (apiStatus(failure) === 409) {
      // Answered elsewhere (another tab) or closed meanwhile (idle, finished).
      notify.failure(failure, 'La sesión ha cambiado', 'Se ha recargado con su estado actual.')
      await refresh()
    }
    else {
      notify.failure(failure, 'No se ha podido responder')
    }
  }
  finally {
    busy.value = false
  }
}

async function onNext() {
  if (next.value === undefined) return
  if (closedByAnswer.value) {
    await refresh() // shows the result
    return
  }
  question.value = next.value
  next.value = undefined
}

async function finish() {
  finishing.value = true
  try {
    session.value = await finishSession(api, id.value)
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido terminar')
  }
  finally {
    finishing.value = false
  }
}

function openItem(itemId: number) {
  if (!session.value) return
  overlay.create(ItemDetailModal).open({ kind: session.value.item_kind, itemId, returnTo: route.fullPath })
}
</script>

<template>
  <AppPanel :title="session?.exercise_name ?? 'Sesión'" :fill="!finished">
    <template #leading>
      <UButton :to="back.to" icon="i-lucide-arrow-left" color="neutral" variant="ghost" :aria-label="back.label" />
    </template>
    <template v-if="session && !finished" #actions>
      <UBadge
        :label="`${score} / ${answered}`"
        color="neutral"
        variant="subtle"
        size="lg"
        icon="i-lucide-circle-check"
        data-testid="score"
      />
      <UButton label="Terminar" icon="i-lucide-square" color="neutral" variant="outline" :loading="finishing" @click="finish" />
    </template>

    <div class="mx-auto flex w-full max-w-4xl flex-1 flex-col">
      <USkeleton v-if="status === 'pending' && !session" class="h-96 w-full" />

      <UEmpty
        v-else-if="apiStatus(error) === 404"
        icon="i-lucide-search-x"
        title="Esta sesión no existe"
        :actions="[{ label: 'Ver tus ejercicios', to: '/exercises' }]"
      />

      <UAlert
        v-else-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="No se ha podido cargar la sesión"
      />

      <div v-else-if="session && finished" class="space-y-6">
        <UCard :ui="{ body: 'space-y-4 text-center' }" data-testid="result">
          <UIcon name="i-lucide-flag" class="size-10 text-primary" />
          <h2 class="text-xl font-semibold text-highlighted">Sesión terminada</h2>
          <p class="text-muted">
            {{ answered }} respondidas · {{ score }} acertadas<template v-if="accuracy !== null"> · {{ accuracy }}%</template>
          </p>
          <p class="text-sm text-dimmed" data-testid="result-when">
            {{ formatDateTime(session.started_at) }} · {{ formatDuration(session.started_at, session.finished_at!) }}
          </p>
          <div class="flex flex-wrap justify-center gap-2">
            <UButton :label="back.label" :to="back.to" color="neutral" variant="outline" />
            <UButton
              v-if="session.exercise_id !== null"
              label="Practicar otra vez"
              icon="i-lucide-rotate-ccw"
              :loading="starting"
              @click="start({ id: session.exercise_id, item_kind: session.item_kind })"
            />
          </div>
        </UCard>

        <section v-if="session.history.length" aria-labelledby="review" class="space-y-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 id="review" class="text-sm font-semibold uppercase tracking-wide text-muted">Repaso</h2>
            <UButton
              v-if="reviewed.length"
              :label="allExpanded ? 'Plegar todas' : 'Desplegar todas'"
              :icon="allExpanded ? 'i-lucide-chevrons-down-up' : 'i-lucide-chevrons-up-down'"
              color="neutral"
              variant="ghost"
              size="sm"
              class="ml-auto"
              data-testid="expand-all"
              @click="expandAll(!allExpanded)"
            />
            <UTabs
              :model-value="onlyMissed ? 'missed' : 'all'"
              :items="reviewTabs"
              :content="false"
              size="sm"
              data-testid="review-filter"
              @update:model-value="onlyMissed = $event === 'missed'"
            />
          </div>
          <p v-if="!reviewed.length" class="text-sm text-muted">No fallaste ninguna.</p>
          <div class="space-y-2">
            <ReviewQuestion
              v-for="item in reviewed"
              :key="item.id"
              v-model:open="expanded[item.id]"
              :question="item"
              @open-item="openItem"
            />
          </div>
        </section>
      </div>

      <UCard v-else-if="exhausted" :ui="{ body: 'space-y-4 text-center' }" data-testid="exhausted">
        <h2 class="text-lg font-semibold text-highlighted">No quedan preguntas</h2>
        <p class="text-muted">
          Las colecciones ya no tienen suficientes elementos activos para otra pregunta.
        </p>
        <UButton label="Terminar la sesión" :loading="finishing" @click="finish" />
      </UCard>

      <component
        :is="player"
        v-else-if="question && player"
        class="flex-1"
        :question="question"
        :busy="busy"
        :back-fields="backFields"
        @answer="onAnswer"
        @next="onNext"
        @open-item="openItem"
      />
    </div>
  </AppPanel>
</template>
