<script setup lang="ts">
import ItemDetailModal from '~/components/ItemDetailModal.vue'
import { PLAYERS } from '~/components/exercise-players'
import type { ExerciseAnswer, ExerciseQuestion } from '~/models/practice'
import { answerQuestion, finishSession, getSession } from '~/services/exercise-sessions'
import { apiStatus } from '~/utils/api-error'

// Play a session: one question at a time, picked by its type's player.
// Answering shows the graded card; "Siguiente" shows the next one, which the
// answer already brought. A finished session shows its result.

const route = useRoute()
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

const finished = computed(() => !!session.value?.finished_at)
const exhausted = computed(() => !finished.value && !question.value)
const player = computed(() => (question.value ? PLAYERS[question.value.type] : null))
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
  overlay.create(ItemDetailModal).open({ kind: session.value.item_kind, itemId })
}
</script>

<template>
  <AppPanel :title="session?.exercise_name ?? 'Sesión'">
    <template #leading>
      <UButton to="/exercises" icon="i-lucide-arrow-left" color="neutral" variant="ghost" aria-label="Volver a los ejercicios" />
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

    <div class="mx-auto max-w-2xl">
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

      <UCard v-else-if="session && finished" :ui="{ body: 'space-y-4 text-center' }" data-testid="result">
        <UIcon name="i-lucide-flag" class="size-10 text-primary" />
        <h2 class="text-xl font-semibold text-highlighted">Sesión terminada</h2>
        <p class="text-muted">
          {{ answered }} respondidas · {{ score }} acertadas<template v-if="accuracy !== null"> · {{ accuracy }}%</template>
        </p>
        <div class="flex flex-wrap justify-center gap-2">
          <UButton label="Volver a los ejercicios" to="/exercises" color="neutral" variant="outline" />
          <UButton
            v-if="session.exercise_id !== null"
            label="Practicar otra vez"
            icon="i-lucide-rotate-ccw"
            :loading="starting"
            @click="start({ id: session.exercise_id, item_kind: session.item_kind })"
          />
        </div>
      </UCard>

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
        :question="question"
        :busy="busy"
        @answer="onAnswer"
        @next="onNext"
        @open-item="openItem"
      />
    </div>
  </AppPanel>
</template>
