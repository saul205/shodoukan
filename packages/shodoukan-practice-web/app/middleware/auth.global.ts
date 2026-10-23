// Every screen requires sign-in; only the provider's redirect back is public.
export default defineNuxtRouteMiddleware(async (to) => {
  if (to.path === '/auth/callback') return
  const auth = useAuth()
  if (await auth.accessToken()) return
  await auth.login(to.fullPath)
  return abortNavigation()
})
