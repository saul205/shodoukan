import { createApiClient } from '~/utils/api-client'

/** The practice API client, with the user's token on every request. */
export default defineNuxtPlugin(() => {
  const auth = useAuth()
  const api = createApiClient({
    baseURL: useRuntimeConfig().public.apiBase,
    getToken: () => auth.accessToken(),
    onUnauthorized: () => auth.login(currentPath()),
  })
  return { provide: { api } }
})

function currentPath(): string {
  return window.location.pathname + window.location.search
}
