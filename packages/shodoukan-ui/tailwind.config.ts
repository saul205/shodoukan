import type { Config } from 'tailwindcss'
import preset from './tailwind-preset'

export default {
  presets: [preset],
  content: ['./src/**/*.{vue,ts}'],
} satisfies Config
