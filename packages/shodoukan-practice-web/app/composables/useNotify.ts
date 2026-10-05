import { apiErrorMessage } from '~/utils/api-error'

/** Short feedback after an action (toasts). */
export function useNotify() {
  const toast = useToast()

  function success(title: string, description?: string) {
    toast.add({ title, description, color: 'success', icon: 'i-lucide-circle-check' })
  }

  /** `fallback` describes failures the server answered (not a 404 or no connection). */
  function failure(error: unknown, title = 'No se ha podido guardar', fallback?: string) {
    toast.add({ title, description: apiErrorMessage(error, fallback), color: 'error', icon: 'i-lucide-circle-alert' })
  }

  return { success, failure }
}
