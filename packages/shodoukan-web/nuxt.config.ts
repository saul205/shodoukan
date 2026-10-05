// Dictionary frontend: a client-only SPA, published as static files (Render
// Static Site). Pages load their data in the browser after navigation, so
// server rendering only produced a "loading" page and a second request.
// apiBase is set at build time with NUXT_PUBLIC_API_BASE.
export default defineNuxtConfig({
  ssr: false,
  modules: ['@nuxtjs/tailwindcss'],
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
    },
  },
  css: ['shodoukan-ui/style.css', '~/assets/css/main.css'],
  tailwindcss: {
    cssPath: ['~/assets/css/main.css', { injectPosition: 0 }],
  },
  compatibilityDate: '2025-06-20',
})
