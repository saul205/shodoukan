import type { Config } from 'tailwindcss'

export default {
  content: [
    './components/**/*.vue',
    './pages/**/*.vue',
    './layouts/**/*.vue',
    './app.vue',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        japanese: ['Noto Sans JP', 'sans-serif'],
      },
    },
  },
} satisfies Config
