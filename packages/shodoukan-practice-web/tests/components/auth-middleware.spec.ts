// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mockNuxtImport } from '@nuxt/test-utils/runtime'
import type { RouteLocationNormalized } from 'vue-router'
import authMiddleware from '../../app/middleware/auth.global'

const { auth } = vi.hoisted(() => ({
  auth: {
    token: 'test-token' as string | null,
    login: vi.fn(async (_returnTo?: string) => {}),
  },
}))

mockNuxtImport('useAuth', () => () => ({
  accessToken: async () => auth.token,
  login: auth.login,
}))

function route(fullPath: string): RouteLocationNormalized {
  const [path] = fullPath.split('?')
  return { path, fullPath } as RouteLocationNormalized
}

beforeEach(() => {
  auth.token = 'test-token'
  auth.login.mockClear()
})

describe('auth middleware', () => {
  it('lets a signed-in user through', async () => {
    const result = await authMiddleware(route('/library'), route('/'))

    expect(result).toBeUndefined()
    expect(auth.login).not.toHaveBeenCalled()
  })

  it('sends a signed-out user to sign in, coming back to the same page', async () => {
    auth.token = null

    const result = await authMiddleware(route('/library/entries/3?collection=2'), route('/'))

    expect(auth.login).toHaveBeenCalledWith('/library/entries/3?collection=2')
    expect(result).not.toBeUndefined() // navigation aborted
  })

  it('never blocks the sign-in callback', async () => {
    auth.token = null

    const result = await authMiddleware(route('/auth/callback?code=x&state=y'), route('/'))

    expect(result).toBeUndefined()
    expect(auth.login).not.toHaveBeenCalled()
  })
})
