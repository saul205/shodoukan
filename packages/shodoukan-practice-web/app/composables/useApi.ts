import type { ApiClient } from '~/utils/api-client'

/** The practice API client (bearer token included). */
export function useApi(): ApiClient {
  return useNuxtApp().$api
}
