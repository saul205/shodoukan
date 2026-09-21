export default defineNuxtConfig({
  modules: ['@nuxtjs/tailwindcss'],
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000',
    },
  },
  css: ['~/assets/css/main.css'],
  compatibilityDate: '2025-06-20',
})
