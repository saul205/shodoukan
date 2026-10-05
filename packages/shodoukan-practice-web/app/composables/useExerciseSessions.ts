import ConfirmModal from '~/components/ConfirmModal.vue'
import type { ItemKind } from '~/models/practice'
import { listSessions, startSession } from '~/services/exercise-sessions'
import { apiStatus } from '~/utils/api-error'

/** The user's open session (at most one), to resume it; null if none. */
export function useOpenSession() {
  const api = useApi()
  const { data, refresh } = useAsyncData('open-exercise-session', async () => {
    const page = await listSessions(api, { status: 'open', limit: 1 })
    return page.items[0] ?? null
  })
  return { session: data, refresh }
}

/**
 * Start an exercise and go to its session. Starting closes the open session,
 * so if there is one the user confirms first.
 */
export function useStartExercise() {
  const api = useApi()
  const notify = useNotify()
  const confirm = useOverlay().create(ConfirmModal)
  const { codeFor } = useMeaningLang()
  const starting = ref(false)

  async function start(exercise: { id: number; item_kind: ItemKind }) {
    starting.value = true
    try {
      const open = (await listSessions(api, { status: 'open', limit: 1 })).items[0]
      if (open) {
        const confirmed = await confirm.open({
          title: '¿Empezar una sesión nueva?',
          description: `Tienes abierta una sesión de «${open.exercise_name}»; se cerrará y quedará en el historial.`,
          confirmLabel: 'Empezar',
        }).result
        if (!confirmed) return
      }
      const session = await startSession(api, exercise.id, codeFor(exercise.item_kind))
      await navigateTo(`/exercise-sessions/${session.id}`)
    }
    catch (error) {
      const fallback = apiStatus(error) === 422
        ? 'Sus colecciones no tienen suficientes elementos activos con los campos que pregunta.'
        : undefined
      notify.failure(error, 'No se ha podido empezar', fallback)
    }
    finally {
      starting.value = false
    }
  }

  return { start, starting }
}
