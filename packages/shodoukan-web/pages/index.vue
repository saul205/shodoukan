<script setup lang="ts">
import { search } from '~/services/search'
import type { SearchResult } from '~/models/search'

const config = useRuntimeConfig()

const query = ref('')
const lang = ref('en')
const results = ref<SearchResult | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

async function handleSearch() {
  if (!query.value.trim()) return
  loading.value = true
  error.value = null
  try {
    results.value = await search(query.value.trim(), config.public.apiBase, lang.value)
  }
  catch {
    error.value = 'Failed to fetch results. Is the API running?'
    results.value = null
  }
  finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="mx-auto w-[80%] px-4 py-10">
    <div class="mb-8 mx-auto max-w-full md:max-w-[60%]">
      <SearchBar v-model="query" v-model:lang="lang" @search="handleSearch" />
    </div>

    <div v-if="loading" class="py-12 text-center text-zinc-500">
      Searching…
    </div>

    <div v-else-if="error" class="py-12 text-center text-red-400">
      {{ error }}
    </div>

    <div
      v-else-if="results"
      class="flex flex-col-reverse gap-6 md:flex-row"
    >
      <div
        v-if="results.kanji.length"
        class="[flex:0] flex flex-wrap gap-3 self-start"
      >
        <KanjiCardCompact
          v-for="k in results.kanji"
          :key="k.literal"
          :kanji="k"
          :lang="lang"
        />
      </div>

      <section class="flex flex-1 flex-col gap-3">
        <EntryCard
          v-for="e in results.entries.items"
          :key="e.id"
          :entry="e"
          :lang="lang"
        />
        <p
          v-if="!results.entries.items.length && !results.kanji.length"
          class="py-12 text-center text-zinc-500"
        >
          No results for "{{ query }}".
        </p>
      </section>
    </div>
  </main>
</template>
