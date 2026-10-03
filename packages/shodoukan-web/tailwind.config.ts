import type { Config } from 'tailwindcss'
import sharedPreset from 'shodoukan-ui/tailwind-preset'

export default {
  presets: [sharedPreset],
  content: [
    './components/**/*.vue',
    './pages/**/*.vue',
    './layouts/**/*.vue',
    './app.vue',
  ],
} satisfies Config
