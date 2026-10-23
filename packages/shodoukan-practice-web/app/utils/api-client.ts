import { $fetch, type $Fetch } from 'ofetch'

export interface ApiClientOptions {
  baseURL: string
  /** The current access token, refreshed if needed; null when signed out. */
  getToken: () => Promise<string | null>
  /** Called on a 401: the session is gone, so sign in again. */
  onUnauthorized: () => void | Promise<void>
}

export type ApiClient = $Fetch

/**
 * `$fetch` for the practice API: adds the bearer token to every request and
 * sends the user back to sign-in when the API answers 401.
 */
export function createApiClient(options: ApiClientOptions): ApiClient {
  return $fetch.create({
    baseURL: options.baseURL,
    async onRequest({ options: request }) {
      const token = await options.getToken()
      if (token) {
        const headers = new Headers(request.headers)
        headers.set('Authorization', `Bearer ${token}`)
        request.headers = headers
      }
    },
    async onResponseError({ response }) {
      if (response.status === 401) await options.onUnauthorized()
    },
  })
}
