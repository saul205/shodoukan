import { describe, expect, it } from 'vitest'
import { FetchError } from 'ofetch'
import { apiErrorMessage, apiStatus } from '../../app/utils/api-error'

const notFound = () => Object.assign(new FetchError('404 Not Found'), { statusCode: 404 })

describe('apiStatus', () => {
  it('reads the status of a failed call, also when wrapped', () => {
    expect(apiStatus(notFound())).toBe(404)
    expect(apiStatus(new Error('wrapped', { cause: notFound() }))).toBe(404)
  })

  it('has none without a response', () => {
    expect(apiStatus(new FetchError('fetch failed'))).toBeUndefined()
    expect(apiStatus(new Error('boom'))).toBeUndefined()
    expect(apiErrorMessage(new Error('boom'))).toBe('No se puede conectar con el servidor.')
  })
})
