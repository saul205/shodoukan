import { safeReturnPath } from '~/utils/return-path'

interface LoginState {
  returnTo?: string
}

/** The signed-in user and the sign-in / sign-out flow. */
export function useAuth() {
  const { manager, user } = useNuxtApp().$auth

  const username = computed(() => {
    const profile = user.value?.profile
    return profile?.preferred_username ?? profile?.name ?? ''
  })

  /** A valid access token, renewing it if it expired; null if signed out. */
  async function accessToken(): Promise<string | null> {
    const current = user.value
    if (!current) return null
    if (!current.expired) return current.access_token
    try {
      const renewed = await manager.signinSilent()
      return renewed?.access_token ?? null
    }
    catch {
      await manager.removeUser()
      return null
    }
  }

  /** Go to the identity provider; come back to `returnTo` afterwards. */
  async function login(returnTo = '/'): Promise<void> {
    const state: LoginState = { returnTo: safeReturnPath(returnTo) }
    await manager.signinRedirect({ state })
  }

  /** Finish the redirect from the identity provider; returns where to go next. */
  async function completeLogin(): Promise<string> {
    const signedIn = await manager.signinRedirectCallback()
    return safeReturnPath((signedIn.state as LoginState | undefined)?.returnTo)
  }

  async function logout(): Promise<void> {
    await manager.signoutRedirect()
  }

  return { user, username, accessToken, login, completeLogin, logout }
}
