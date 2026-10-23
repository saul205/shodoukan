import { UserManager, WebStorageStateStore, type User } from 'oidc-client-ts'
import { resolveAuthority } from '~/utils/auth-authority'

/**
 * OpenID Connect sign-in (authorization code + PKCE) against the identity
 * provider in `authIssuer` (Keycloak locally; a path like `/idp/realms/...`
 * when deployed behind the same host). Tokens are kept in
 * sessionStorage and renewed in the background with the refresh token.
 */
export default defineNuxtPlugin(async () => {
  const config = useRuntimeConfig().public
  const origin = window.location.origin

  const manager = new UserManager({
    authority: resolveAuthority(config.authIssuer, origin),
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
