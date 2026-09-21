<script setup lang="ts">
import { SUPPORTED_LANGUAGES } from '~/models/kanji'

defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <select
    :value="modelValue"
    class="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-3 text-sm text-zinc-100 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
    @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
  >
    <option
      v-for="lang in SUPPORTED_LANGUAGES"
      :key="lang.code"
      :value="lang.code"
    >
      {{ lang.label }}
    </option>
  </select>
</template>
