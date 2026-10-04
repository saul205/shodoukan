import { FetchError } from 'ofetch'

/** The HTTP status of a failed API call, if it got a response. */
export function apiStatus(error: unknown): number | undefined {
  return error instanceof FetchError ? error.statusCode ?? error.response?.status : undefined
}

/** A message to show the user for a failed API call. */
export function apiErrorMessage(error: unknown, fallback = 'Algo ha fallado. Inténtalo de nuevo.'): string {
  const status = apiStatus(error)
  if (status === undefined) return 'No se puede conectar con el servidor.'
  if (status === 404) return 'No se ha encontrado.'
  return fallback
}
