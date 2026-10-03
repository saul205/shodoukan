// Practice frontend: a client-only SPA behind Keycloak sign-in.
// Every screen needs the signed-in user's token, which lives in the browser,
// so server-side rendering would add nothing (see docs/practice/technical/frontend.md).
export default defineNuxtConfig({
  modules: ['@nuxt/ui'],
  ssr: false,
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  devServer: { port: 3001 },
  // Overridable with NUXT_PUBLIC_API_BASE, NUXT_PUBLIC_AUTH_ISSUER, NUXT_PUBLIC_AUTH_CLIENT_ID.
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8001',
      authIssuer: 'http://localhost:8080/realms/shodoukan',
      authClientId: 'shodoukan-practice-web',
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'es' },
      title: 'Shodoukan · Práctica',
    },
  },
  colorMode: { preference: 'dark' },
  compatibilityDate: '2026-10-01',
})
