import { apiErrorMessage } from '~/utils/api-error'

/** Short feedback after an action (toasts). */
export function useNotify() {
  const toast = useToast()

  function success(title: string, description?: string) {
    toast.add({ title, description, color: 'success', icon: 'i-lucide-circle-check' })
  }

  function failure(error: unknown, title = 'No se ha podido guardar') {
    toast.add({ title, description: apiErrorMessage(error), color: 'error', icon: 'i-lucide-circle-alert' })
  }

  return { success, failure }
}
