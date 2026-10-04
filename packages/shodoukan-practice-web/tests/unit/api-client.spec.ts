import { afterEach, describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../../app/utils/api-client'

function respond(status: number, body: unknown = {}) {
  return vi.fn(async () => new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('createApiClient', () => {
  it('sends the bearer token and the base URL', async () => {
    const fetchMock = respond(200, { ok: true })
    vi.stubGlobal('fetch', fetchMock)
    const api = createApiClient({
      baseURL: 'http://api.test',
      getToken: async () => 'abc',
      onUnauthorized: vi.fn(),
    })

    const body = await api('/users/me')

    expect(body).toEqual({ ok: true })
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://api.test/users/me')
    expect(new Headers(init.headers).get('Authorization')).toBe('Bearer abc')
  })

  it('sends no Authorization header when signed out', async () => {
    const fetchMock = respond(200)
    vi.stubGlobal('fetch', fetchMock)
    const api = createApiClient({ baseURL: 'http://api.test', getToken: async () => null, onUnauthorized: vi.fn() })

    await api('/dictionary/search')

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(new Headers(init.headers).has('Authorization')).toBe(false)
  })

  it('asks to sign in again on a 401, and still rejects', async () => {
    vi.stubGlobal('fetch', respond(401, { detail: 'invalid token' }))
    const onUnauthorized = vi.fn()
    const api = createApiClient({ baseURL: 'http://api.test', getToken: async () => 'old', onUnauthorized })

    await expect(api('/library/entries')).rejects.toThrow()
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it('does not ask to sign in on other errors', async () => {
    vi.stubGlobal('fetch', respond(409, { detail: 'taken' }))
    const onUnauthorized = vi.fn()
    const api = createApiClient({ baseURL: 'http://api.test', getToken: async () => 'abc', onUnauthorized })

    await expect(api('/collections/entries', { method: 'POST' })).rejects.toThrow()
    expect(onUnauthorized).not.toHaveBeenCalled()
  })
})
