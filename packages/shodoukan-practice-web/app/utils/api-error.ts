import { FetchError } from 'ofetch'

/**
 * The HTTP status of a failed API call, if it got a response. Also reads it
 * through `useAsyncData`'s error, which wraps the original one in `cause`.
 */
export function apiStatus(error: unknown): number | undefined {
  if (error instanceof FetchError) return error.statusCode ?? error.response?.status
  if (error instanceof Error && error.cause !== undefined) return apiStatus(error.cause)
  return undefined
}

/** A message to show the user for a failed API call. */
export function apiErrorMessage(error: unknown, fallback = 'Algo ha fallado. Inténtalo de nuevo.'): string {
  const status = apiStatus(error)
  if (status === undefined) return 'No se puede conectar con el servidor.'
  if (status === 404) return 'No se ha encontrado.'
  return fallback
}
