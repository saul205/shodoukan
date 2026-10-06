export default defineNuxtConfig({
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
  // The sources page was merged into About.
  routeRules: {
    '/sources': { redirect: '/about' },
  },
  compatibilityDate: '2025-06-20',
})
