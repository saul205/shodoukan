/**
 * A library item loaded when `key` changes and then replaced by each edit's
 * response (the API returns the whole item after every change).
 */
export function useEditableItem<T>(key: () => string, load: () => Promise<T>) {
  const notify = useNotify()

  const item = shallowRef<T | null>(null)
  const status = ref<'pending' | 'success' | 'error'>('pending')
  const saving = ref(false)

  async function refresh() {
    status.value = 'pending'
    try {
      item.value = await load()
      status.value = 'success'
    }
    catch {
      item.value = null
      status.value = 'error'
    }
  }

  watch(key, refresh, { immediate: true })

  /** Run an edit; on success the item becomes what the API returned. */
  async function save(edit: () => Promise<T>): Promise<boolean> {
    saving.value = true
    try {
      item.value = await edit()
      return true
    }
    catch (failure) {
      notify.failure(failure)
      return false
    }
    finally {
      saving.value = false
    }
  }

  return { item, status, saving, save, refresh }
}
