import { computed, shallowRef } from 'vue'

// A signed-in `useAuth()` for component tests, so the app's sign-in
// middleware lets them through without an identity provider.
// Use with `mockNuxtImport('useAuth', () => signedInAuth)`.
export function signedInAuth() {
  return {
    user: shallowRef(null),
    username: computed(() => 'dev'),
    accessToken: async () => 'test-token',
    login: async () => {},
    completeLogin: async () => '/',
    logout: async () => {},
  }
}
