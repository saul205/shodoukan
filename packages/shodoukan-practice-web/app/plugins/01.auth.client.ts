import { UserManager, WebStorageStateStore, type User } from 'oidc-client-ts'

/**
 * OpenID Connect sign-in (authorization code + PKCE) against the identity
 * provider in `authIssuer` (Keycloak locally). Tokens are kept in
 * sessionStorage and renewed in the background with the refresh token.
 */
export default defineNuxtPlugin(async () => {
  const config = useRuntimeConfig().public
  const origin = window.location.origin

  const manager = new UserManager({
    authority: config.authIssuer,
    client_id: config.authClientId,
    redirect_uri: `${origin}/auth/callback`,
    post_logout_redirect_uri: `${origin}/`,
    response_type: 'code',
    scope: 'openid profile',
    automaticSilentRenew: true,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  })

  const user = shallowRef<User | null>(await manager.getUser())
  manager.events.addUserLoaded((loaded) => {
    user.value = loaded
  })
  manager.events.addUserUnloaded(() => {
    user.value = null
  })

  return { provide: { auth: { manager, user } } }
})
