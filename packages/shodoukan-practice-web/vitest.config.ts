import { defineVitestConfig } from '@nuxt/test-utils/config'

// Plain unit tests run in happy-dom. Component tests that need Nuxt (Nuxt UI
// components, auto-imports) start with `// @vitest-environment nuxt`.
export default defineVitestConfig({
  test: {
    environment: 'happy-dom',
    include: ['tests/**/*.spec.ts'],
  },
})
