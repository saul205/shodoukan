<script setup lang="ts">
defineProps<{ modelValue: string; lang: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:lang': [value: string]
  search: []
}>()
</script>

<template>
  <div class="flex flex-wrap gap-2">
    <input
      type="search"
      :value="modelValue"
      placeholder="Search kanji, romaji, hiragana…"
      class="flex-1 min-w-[10rem] rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-3 text-lg text-zinc-100 placeholder-zinc-500 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @keydown.enter="emit('search')"
    />
    <div class="flex flex-1 justify-center gap-2">
      <LanguageSelector
        :model-value="lang"
        class="min-w-max"
        @update:model-value="emit('update:lang', $event)"
      />
      <button
        class="rounded-lg bg-indigo-600 px-5 py-3 font-medium text-white transition hover:bg-indigo-500 active:bg-indigo-700"
        @click="emit('search')"
      >
        Search
      </button>
    </div>
  </div>
</template>
